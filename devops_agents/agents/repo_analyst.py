from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import InjectedState
from pydantic import BaseModel, Field
from tools.git_tools import AsyncGitTools
from app.kafka_terminal_producer import send_terminal_message
from config.settings import settings
from typing import Annotated, Optional, List
from langgraph.prebuilt import ToolNode

# ============== SCHEMA ==============
class RepoAnalysisOutput(BaseModel):
    """Structured output from repository analysis for Dockerfile generation."""
    project_type: str = Field(..., description="Project type: 'node' or 'springboot'")
    version: str = Field(..., description="Runtime version (e.g. '18' for Node, '17' for Java)")
    package_manager: str = Field(..., description="Package manager: npm, yarn, pnpm, maven, gradle")
    build_command: str = Field("", description="Build command (e.g. 'npm run build', 'mvn clean package'). Empty if no build needed.")
    run_command: str = Field(..., description="Start command (e.g. 'npm start', 'java -jar app.jar')")
    port: int = Field(..., description="Application port (e.g. 3000, 8080)")
    env_variables: List[str] = Field(default_factory=list, description="Required environment variable keys")
    has_lockfile: bool = Field(False, description="Whether a lockfile exists (package-lock.json, yarn.lock, etc.)")
    framework: Optional[str] = Field(None, description="Detected framework: next, nest, express, spring-boot, etc.")
    needs_build_step: bool = Field(False, description="True if build step creates output (TypeScript, Next.js, NestJS). False for plain JS apps that run directly.")
    health_check_path: str = Field("/", description="Path for liveness/readiness probes (e.g. '/', '/health', '/api/status')")
    cpu_limit: str = Field("200m", description="CPU limit for K8s (e.g. '200m', '500m')")
    memory_limit: str = Field("256Mi", description="Memory limit for K8s (e.g. '256Mi', '512Mi')")

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
SYSTEM_PROMPT = """You are a DevOps expert analyzing a repository to generate a Dockerfile.

Your task:
1. Look at the file_list provided to understand what files exist in the repository.
2. Use the read_file tool to read relevant configuration files.
3. Extract the information needed for Dockerfile generation.
4. Call the RepoAnalysisOutput tool with your findings.

## For Node.js Projects (package.json exists):
- Read: package.json, tsconfig.json (if exists), .env.example (if exists)
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
- Read: pom.xml or build.gradle
- Read: src/main/resources/application.properties or application.yml (if exists)
- Extract: Java version, build command, port (server.port)
- needs_build_step is always TRUE for Spring Boot

## INTELLIGENCE RULES (Resources & Health):
1. **Health Check Path**:
   - Spring Boot: default to `/actuator/health` or `/health`
   - Node/Express: Look for `app.get('/health')` or use `/`
   - Next.js: use `/`
2. **Resources (CPU/Memory)**:
   - **Java/Spring Boot**: logic heavy. Set memory="512Mi", cpu="500m"
   - **Node.js**: lightweight. Set memory="256Mi", cpu="200m"
   - **NestJS**: moderate. Set memory="384Mi", cpu="300m"

## Rules:
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
        model="gpt-5-mini",
        api_key=settings.openai_key,
        temperature=0
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
            
        initial_human_message = HumanMessage(content=f"Analyze this repository. Here are the files:\n\n{file_list_str}")
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
    
    try:
        last_message = state["messages"][-1]
        output_args = last_message.tool_calls[0]["args"]
        analysis = RepoAnalysisOutput(**output_args)
        
        # Send summary to frontend
        summary = f"""✅ Repository Analysis Complete
                    📦 Project Type: {analysis.project_type}
                    🔧 Framework: {analysis.framework or 'N/A'}
                    📌 Version: {analysis.version}
                    🚀 Port: {analysis.port}
                    📝 Package Manager: {analysis.package_manager}
                    """
        send_terminal_message(project_id, summary)
        
        return {"analyzed_repository_details": analysis}
        
    except Exception as e:
        send_terminal_message(project_id, f"❌ Analysis validation failed: {str(e)}\n\r")
        return {"build_status": "analysis_validation_failed"}

def check_analysis_finish(state):
    """Route based on agent output."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
        if last_message.tool_calls[0]["name"] == "RepoAnalysisOutput":
            return "finalize_analysis"
        return "repo_analysis_tool"
    return "repo_analysis_agent"