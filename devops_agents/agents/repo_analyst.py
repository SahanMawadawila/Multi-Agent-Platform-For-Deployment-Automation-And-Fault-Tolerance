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
    build_command: str = Field("", description="Build command (e.g. 'npm run build', 'mvn clean package')")
    run_command: str = Field(..., description="Start command (e.g. 'npm start', 'java -jar app.jar')")
    port: int = Field(..., description="Application port (e.g. 3000, 8080)")
    env_variables: List[str] = Field(default_factory=list, description="Required environment variable keys")
    has_lockfile: bool = Field(False, description="Whether a lockfile exists (package-lock.json, yarn.lock, etc.)")
    framework: Optional[str] = Field(None, description="Detected framework: next, nest, express, spring-boot, etc.")

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
- Check for lockfiles: package-lock.json, yarn.lock, pnpm-lock.yaml
- Detect framework from dependencies: next, nest, express
- Extract: version (from engines or default to 18), scripts (build, start), port

## For Spring Boot Projects (pom.xml or build.gradle exists):
- Read: pom.xml or build.gradle
- Read: src/main/resources/application.properties or application.yml (if exists)
- Extract: Java version, build command, port (server.port)

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
        model="gpt-5.1-mini",
        api_key=settings.openai_key,
        temperature=0
    )
    llm_with_tools = llm.bind_tools(tools)
    
    # Build messages for LLM
    if not messages:
        # First call - include system prompt and file list
        file_list_str = "\n".join(f"- {f}" for f in file_list)
        llm_messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Analyze this repository. Here are the files:\n\n{file_list_str}")
        ]
    else:
        # Subsequent calls - continue conversation
        llm_messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    
    # Get LLM response
    response = await llm_with_tools.ainvoke(llm_messages)
    
    return {"messages": [response]}

# ============== GRAPH HELPERS ==============
def repo_analysis_tool_node(state):
    """Execute tools with state injection."""
    node = ToolNode(tools)
    return node.invoke(state)

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