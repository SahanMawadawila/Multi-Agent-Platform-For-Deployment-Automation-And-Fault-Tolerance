from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import InjectedState
from pydantic import BaseModel, Field
from tools.git_tools import AsyncGitTools
from app.kafka_terminal_producer import send_terminal_message
from config.settings import settings
from typing import Annotated, Optional, List, Dict
from langgraph.prebuilt import ToolNode

# ============== SCHEMA ==============
class DatabaseCredentials(BaseModel):
    """Extracted database credentials if found in the repository configuration."""
    db_user: str = Field("", description="Username for the database connection. Empty string if not found.")
    db_password: str = Field("", description="Password for the database connection. Empty string if not found.")
    db_name: str = Field("", description="Name of the database. Empty string if not found.")
    db_root_password: str = Field("", description="Root password for the database if explicitly specified. Empty string if not found.")

class RepoAnalysisOutput(BaseModel):
    """Structured output from repository analysis for Dockerfile generation and database deployment."""
    project_type: str = Field(..., description="Project type: 'node' or 'springboot'")
    version: str = Field(..., description="Runtime version (e.g. '18' for Node, '17' for Java)")
    package_manager: str = Field(..., description="Package manager: npm, yarn, pnpm, maven, gradle")
    build_command: str = Field("", description="Build command (e.g. 'npm run build', 'mvn clean package'). Empty if no build needed.")
    run_command: str = Field(..., description="Start command (e.g. 'npm start', 'java -jar app.jar')")
    port: int = Field(..., description="Application port (e.g. 3000, 8080)")
    env_variables: List[str] = Field(default_factory=list, description="All environment variables in the application exactly as they appear in the `.env` files or default configurations. Format: ['KEY=VALUE', 'KEY2=VALUE2']")
    has_lockfile: bool = Field(False, description="Whether a lockfile exists (package-lock.json, yarn.lock, etc.)")
    framework: Optional[str] = Field(None, description="Detected framework: next, nest, express, spring-boot, etc.")
    needs_build_step: bool = Field(False, description="True if build step creates output (TypeScript, Next.js, NestJS). False for plain JS apps that run directly.")
    health_check_path: str = Field("/", description="Path for liveness/readiness probes (e.g. '/', '/health', '/api/status')")
    cpu_limit: str = Field("200m", description="CPU limit for K8s (e.g. '200m', '500m')")
    memory_limit: str = Field("256Mi", description="Memory limit for K8s (e.g. '256Mi', '512Mi')")
    # Database detection
    needs_database: bool = Field(False, description="True if the project uses a database (detected from dependencies, env vars, or config). False if no DB is needed or DB URL points to an external managed service.")
    database_type: str = Field("", description="Database type if needs_database: 'mongodb', 'postgresql', 'mysql'. Empty if not needed.")
    database_env_variables: List[str] = Field(default_factory=list, description="Environment variables read from .env file used for database configurations. Format: ['KEY=VALUE']")
    database_credentials: DatabaseCredentials = Field(default_factory=DatabaseCredentials, description="Explicitly extracted database credentials (username, password, db name).")

# ============== TOOL ==============
@tool
async def read_file(
    file_path: str, 
    state: Annotated[dict, InjectedState]
) -> str:
    """Reads a file from the repository.
    
    Args:
        file_path: Relative path to the file (e.g., 'package.json', 'pom.xml', 'src/main/resources/application.properties')
    
    Returns:
        The file content as a string, or an error message if not found.
    """
    local_path = state["local_path"]
    project_id = state.get("project_id", "")
    
    # Send terminal message for each file read
    send_terminal_message(project_id, f"📖 Reading {file_path}\n\r")
    
    result = await AsyncGitTools.read_file(local_path, file_path)
    return result

# Tools list for the graph
tools = [read_file, RepoAnalysisOutput]

# ============== AGENT ==============
SYSTEM_PROMPT = """You are a DevOps expert analyzing a repository to generate a Dockerfile and detect database requirements.

## Steps to follow:
1. Look at the file_list provided to understand what files exist in the repository.
2. Use the read_file tool to read relevant configuration files, ESPECIALLY any `.env`, `.env.example`, or `.env.local` files to find environment variables.
3. Extract the information needed for Dockerfile generation.
4. Detect database requirements and compute database env overrides.
5. Call the RepoAnalysisOutput tool with your findings.

## For Node.js Projects (package.json exists):
- Read: package.json, tsconfig.json (if exists)
- YOU MUST READ: `.env` or `.env.example` (if they exist in the file list)
- Check if lockfiles exist in the provided file list (e.g., package-lock.json, yarn.lock). DO NOT read lockfiles using the read_file tool as they are too large.
- Detect framework from dependencies: next, nest, express
- Extract: version (from engines or default to 18), scripts (build, start), port

### CRITICAL: Determining needs_build_step
Look at the "build" script in package.json:
- Set needs_build_step=TRUE if build creates actual output:
  * TypeScript projects (tsconfig.json exists and build uses tsc/ts-node)
  * Next.js (next build creates .next folder)
  * NestJS (nest build creates dist folder)
  * Build script contains: tsc, webpack, vite build, next build, nest build
  
- Set needs_build_step=FALSE if:
  * No build script exists
  * Build script just echoes a message or runs tests
  * Plain JavaScript project with just index.js
  * Build script is just "echo" or placeholder

### CRITICAL: Run Command
- Look at "start" and "main" in package.json
- If main is "index.js", run_command should be "node index.js"
- If scripts.start exists, use "npm start"

## For Spring Boot Projects (pom.xml or build.gradle exists):
- Read: pom.xml/build.gradle, src/main/resources/application.properties, src/main/resources/application.yml (if they exist)
- YOU MUST READ: `.env` or `.env.example` (if they exist in the file list)
- Extract: Java version, build tool (maven/gradle), port (from properties/yml, default 8080)
- needs_build_step is always TRUE for Spring Boot

## INTELLIGENCE RULES (Resources & Health):
1. **Health Check Path (CRITICAL FOR K8s LIVENESS PROBES)**:
   - You MUST NOT guess or assume this route. A wrong guess will cause the pod to crash infinitely.
   - For Node/Express/NestJS: You MUST read the main server file (e.g. `src/index.js`, `main.ts`, `app.js`) to discover the exact route defined. Look for strings like `.get('/health'`, `.get('/api/liveness'`, etc.
   - For Spring Boot: Default to `/actuator/health`. If you see a custom `HealthController`, use its exact route.
   - Do NOT assume the route starts with `/api` unless you explicitly see it in the code. Output the exact, fully qualified relative route. Only fallback to `/` if absolutely no routes are found.
2. **Resources (CPU/Memory)**:
   - **Java/Spring Boot**: logic heavy. Set memory="512Mi", cpu="500m"
   - **Node.js**: lightweight. Set memory="256Mi", cpu="200m"
   - **NestJS**: moderate. Set memory="384Mi", cpu="300m"

## DATABASE DETECTION & ENVIRONMENT VARIABLES (CRITICAL):
You MUST actively use the `read_file` tool to inspect `.env`, `.env.example`, or `.env.local` if they appear in the file list. If you do not read these files, you will fail to extract the required environment variables.

### When needs_database = TRUE:
- Dependencies include: mongoose, mongodb, pg, mysql2, typeorm, prisma, sequelize, spring-data-mongodb, spring-data-jpa
- Env vars reference localhost/local DB: `MONGODB_URI=mongodb://localhost:27017/mydb`, `DATABASE_URL=postgresql://localhost:5432/db`
- docker-compose.yml contains database services

### When needs_database = FALSE:
- No database dependencies found
- DB URL points to external managed service: atlas.mongodb.net, rds.amazonaws.com, supabase.co, neon.tech, planetscale.com
- Frontend-only project

### database_type:
- Detect from connection string protocol or package: mongodb, postgresql, mysql

### database_env_variables:
If needs_database is TRUE, extract the database environment variables *exactly* as they appear in the `.env` files. 

CRITICAL: You must format this as a JSON list of strings (e.g. `["KEY=value"]`). 
Examples:
- `["MONGODB_URI=mongodb://localhost:27017/mydb", "DB_NAME=mydb"]`
- `["DB_HOST=localhost", "DB_USER=root", "DB_PASS=pass"]`

If needs_database is FALSE, leave database_env_variables empty.

### database_credentials:
If needs_database is TRUE, you must also deeply analyze the `database_env_variables` you just extracted.
Extract the exact username, password, database name, and root password (if applicable) and place them into the `database_credentials` object.
If a specific credential (like `db_user` or `db_password`) is NOT specified in the `.env` files, you MUST return a blank string `""` for that field. Do not guess or make up passwords here.

### env_variables:
Extract ALL OTHER environment variables found in the application's `.env` files or configurations (e.g. `PORT`, `JWT_SECRET`, `API_KEY`).
CRITICAL: You must format this as a JSON list of strings (e.g. `["KEY=value"]`).
Examples:
- `["PORT=3000", "JWT_SECRET=mysecret123"]`

## Rules
- If you cannot find information, use sensible defaults
- Always call RepoAnalysisOutput at the end with your analysis
- Be concise in tool usage - only read files that are necessary
"""

async def repo_analysis_agent(state):
    """LLM-powered repo analyzer that reads files and returns structured output."""
    
    project_id = state.get("project_id", "")
    file_list = state.get("file_list", [])
    messages = state.get("messages", [])
    
    # Send terminal message on first run
    if not messages:
        send_terminal_message(project_id, "🔍 Started analyzing project...\n\r")
    
    # Build the LLM
    llm = ChatOpenAI(
        model="o4-mini",
        api_key=settings.openai_key,
    )
    llm_with_tools = llm.bind_tools(tools)
    
    # Build messages for LLM
    if not messages:
        # First call - include system prompt and file list
        # Truncate file list if it's too long to prevent context overflow
        if len(file_list) > 1000:
            file_list_str = "\n".join(f"- {f}" for f in file_list[:1000]) + f"\n\n... (truncated {len(file_list) - 1000} more files)"
        else:
            file_list_str = "\n".join(f"- {f}" for f in file_list)
            
        component_name = state.get("component_name", project_id)
        component_context = f"\nComponent name: {component_name}\n" if component_name else ""
        initial_human_message = HumanMessage(content=f"Analyze this repository.{component_context}Here are the files:\n\n{file_list_str}")
        llm_messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            initial_human_message
        ]
        
        # Get LLM response
        response = await llm_with_tools.ainvoke(llm_messages)
        return {"messages": [initial_human_message, response]}
    else:
        # Subsequent calls - continue conversation
        llm_messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        
        # Get LLM response
        response = await llm_with_tools.ainvoke(llm_messages)
        return {"messages": [response]}

# ============== GRAPH HELPERS ==============
async def repo_analysis_tool_node(state):
    """Execute tools with state injection."""
    node = ToolNode(tools)
    return await node.ainvoke(state)

def finalize_analysis(state):
    """Extract RepoAnalysisOutput from the last tool call and send summary to frontend."""
    project_id = state.get("project_id", "")
    component_name = state.get("component_name")
    
    try:
        last_message = state["messages"][-1]
        output_args = last_message.tool_calls[0]["args"]
        analysis = RepoAnalysisOutput(**output_args)
        
        # Send summary to frontend
        db_info = f"\n\r  🗄️ Database: {analysis.database_type}" if analysis.needs_database else ""
        summary = (
            f"✅ Repository Analysis Complete\n\r"
            f"  📦 Project Type: {analysis.project_type}\n\r"
            f"  🔧 Framework: {analysis.framework or 'N/A'}\n\r"
            f"  📌 Version: {analysis.version}\n\r"
            f"  🚀 Port: {analysis.port}\n\r"
            f"  📝 Package Manager: {analysis.package_manager}{db_info}\n\r"
        )
        send_terminal_message(project_id, summary, component_name)
        
        # Replace localhost/127.0.0.1 with the dynamic K8s database service name
        computed_db_overrides = {}
        if analysis.needs_database and analysis.database_env_variables:
            # Construct the dynamic K8s service name that the database will be deployed as
            service_name_prefix = f"{component_name}-" if component_name else "app-"
            db_service_name = f"{service_name_prefix}db-{analysis.database_type}"
            
            for item in analysis.database_env_variables:
                if "=" in item:
                    key, val = item.split("=", 1)
                    key = key.strip()
                    val = val.strip()
                    # Replace local hosts with the K8s service name
                    new_val = val.replace("localhost", db_service_name).replace("127.0.0.1", db_service_name)
                    computed_db_overrides[key] = new_val
        
        #existing overrides means 
        existing_overrides = state.get("overridden_envs") or {}
        merged_overrides = {**existing_overrides, **computed_db_overrides}

        print("--- ENV VARIABLE EXTRACTION ---", flush=True)
        print("database env overrides (raw from LLM):", analysis.database_env_variables, flush=True)
        print("database env overrides (modified for K8s):", computed_db_overrides, flush=True)
        print("all other env variables (raw from LLM):", analysis.env_variables, flush=True)
        print("-------------------------------", flush=True)
        
        # Return analysis, DB state fields, merged env overrides, AND resolve the tool message
        return {
            "analyzed_repository_details": analysis,
            "needs_database": analysis.needs_database,
            "database_type": analysis.database_type,
            "database_credentials": analysis.database_credentials.model_dump(),
            "overridden_envs": merged_overrides,
            "messages": [ToolMessage(tool_call_id=last_message.tool_calls[0]["id"], content="Analysis completed successfully.")]
        }
        
    except Exception as e:
        send_terminal_message(project_id, f"❌ Analysis validation failed: {str(e)}\n\r", component_name)
        return {"build_status": "analysis_validation_failed"}

def check_analysis_finish(state):
    """Route based on agent output."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
        if last_message.tool_calls[0]["name"] == "RepoAnalysisOutput":
            return "finalize_analysis"
        return "repo_analysis_tool"
    return "repo_analysis_agent"