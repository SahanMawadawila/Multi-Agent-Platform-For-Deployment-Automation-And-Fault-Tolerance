"""
Application Error Fixer Agent

Fixes application source code errors detected during deployment.
This agent has access to the application's source repository (mirror clone)
and can read/modify/push source files to fix issues like:
- Missing files/directories (e.g., nginx logs directory)
- Bad configuration files (nginx.conf, application.yml)
- Missing dependencies
- Application code bugs causing crashes
"""

import os
import subprocess
import logging
from typing import Annotated, Optional
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import InjectedState, ToolNode
from pydantic import BaseModel, Field
from tools.git_tools import AsyncGitTools
from app.kafka_terminal_producer import send_terminal_message
from config.settings import settings

logger = logging.getLogger("app_error_fixer_agent")


# ============== TOOLS ==============

@tool
async def read_app_file_structure(state: Annotated[dict, InjectedState]) -> str:
    """Returns the current list of files in the application source repository."""
    local_path = state["app_local_path"]
    files = await AsyncGitTools.list_files(local_path)
    return "\n".join(files)


@tool
async def read_app_file(
    file_path: str,
    state: Annotated[dict, InjectedState],
) -> str:
    """Reads a file from the application source repository.

    Args:
        file_path: Relative path to the file (e.g., 'nginx.conf', 'src/main/resources/application.yml')
    """
    local_path = state["app_local_path"]
    project_id = state.get("project_id", "")
    component_name = state.get("component_name", "")
    send_terminal_message(project_id, f"📖 Reading {file_path}\n\r", component_name)
    return await AsyncGitTools.read_file(local_path, file_path)


@tool
async def write_app_file(
    file_path: str,
    content: str,
    state: Annotated[dict, InjectedState],
) -> str:
    """Writes content to a file in the application source repository.

    Args:
        file_path: Relative path to the file
        content: The content to write to the file
    """
    local_path = state["app_local_path"]
    project_id = state.get("project_id", "")
    component_name = state.get("component_name", "")

    full_path = os.path.join(local_path, file_path)
    parent = os.path.dirname(full_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

    send_terminal_message(project_id, f"✏️ Updated {file_path}\n\r", component_name)
    return f"Successfully wrote to {file_path}"


@tool
async def search_app_files(
    query: str,
    state: Annotated[dict, InjectedState],
) -> str:
    """Searches for a query string across the application source repository.

    Args:
        query: The search string or pattern to look for
    """
    local_path = state["app_local_path"]
    project_id = state.get("project_id", "")
    component_name = state.get("component_name", "")
    send_terminal_message(project_id, f"🔎 Searching for '{query}'\n\r", component_name)
    return await AsyncGitTools.search_files(local_path, query)


@tool
async def commit_and_push_app(
    commit_message: str,
    state: Annotated[dict, InjectedState],
) -> str:
    """Commits and pushes all changes to the application source repository.

    Args:
        commit_message: The commit message for the changes
    """
    local_path = state["app_local_path"]
    project_id = state.get("project_id", "")
    component_name = state.get("component_name", "")

    send_terminal_message(project_id, "📤 Pushing application fixes to repository...\n\r", component_name)

    try:
        subprocess.run(["git", "add", "."], cwd=local_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=local_path, check=True, capture_output=True,
        )
        subprocess.run(["git", "push"], cwd=local_path, check=True, capture_output=True)
        return "Successfully committed and pushed changes"
    except subprocess.CalledProcessError as e:
        return f"Error pushing changes: {e.stderr.decode() if e.stderr else str(e)}"


class AppFixComplete(BaseModel):
    """Signal that the application fix has been applied and pushed."""
    summary: str = Field(..., description="Brief summary of what was fixed in the application code")


app_tools = [read_app_file_structure, read_app_file, write_app_file, search_app_files, commit_and_push_app, AppFixComplete]


# ============== AGENT PROMPT ==============

APP_ERROR_FIXER_PROMPT = """You are an expert Software Engineer fixing an application deployment error.
The application was built and deployed to Kubernetes, but is crashing at runtime due to an issue in the application source code or configuration.

You have access to the application's SOURCE REPOSITORY (not the Kubernetes manifests). 

Follow this Chain of Thought process:
1. IDENTIFY: Read the provided deployment error logs carefully. Understand what file or config is causing the crash.
2. EXPLORE: Use `read_app_file_structure` and `read_app_file` to inspect the relevant source files.
3. THINK: Think step-by-step about what change is needed in the source code to fix the error.
4. FIX: Use `write_app_file` to apply the fix. Common fixes include:
   - Creating missing files/directories (e.g., adding a `logs/.keep` file)
   - Fixing configuration files (e.g., nginx.conf, application.yml)
   - Adding missing dependencies to package.json, pom.xml, etc.
   - Fixing build scripts or Dockerfiles
5. PUSH: Use `commit_and_push_app` to push your fix. This will trigger a CI/CD rebuild of the container image.
6. COMPLETE: Call `AppFixComplete` to signal you are done.

IMPORTANT: After you push, a new container image will be built automatically. Do NOT try to fix Kubernetes manifests — that is handled by a separate agent.
"""


# ============== MAIN RUNNER ==============

async def run_app_error_fixer(
    project_id: str,
    component_name: str,
    error_logs: str,
    app_local_path: str,
) -> dict:
    """
    Run the app error fixer agent for a single component.
    
    Args:
        project_id: Project identifier
        component_name: Name of the failing component
        error_logs: Error logs for this component
        app_local_path: Local filesystem path to the application source mirror
        
    Returns:
        dict with 'fixed' (bool) and 'summary' (str)
    """
    send_terminal_message(project_id, f"🔧 Fixing application error for: {component_name}...\n\r")
    
    llm = ChatOpenAI(model="o4-mini", api_key=settings.openai_key)
    llm_with_tools = llm.bind_tools(app_tools)
    
    # Build initial state for tool injection
    tool_state = {
        "app_local_path": app_local_path,
        "project_id": project_id,
        "component_name": component_name,
    }
    
    # Start conversation
    messages = [
        SystemMessage(content=APP_ERROR_FIXER_PROMPT),
        HumanMessage(content=(
            f"Component '{component_name}' is crashing with this error:\n\n"
            f"{error_logs}\n\n"
            f"Please analyze the source code and fix the issue."
        )),
    ]
    
    # Agentic loop (max 20 iterations to prevent infinite loops)
    for iteration in range(20):
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)
        
        if not hasattr(response, "tool_calls") or not response.tool_calls:
            # No tool calls — agent is done or confused, break
            break
        
        # Process tool calls
        for tc in response.tool_calls:
            if tc["name"] == "AppFixComplete":
                summary = tc["args"].get("summary", "Fix applied")
                send_terminal_message(
                    project_id,
                    f"✅ Application fix applied for {component_name}: {summary}\n\r",
                )
                return {"fixed": True, "summary": summary}
            
            # Execute the tool
            tool_node_state = {**tool_state, "messages": [response]}
            node = ToolNode(app_tools)
            try:
                result = await node.ainvoke(tool_node_state)
                for msg in result.get("messages", []):
                    messages.append(msg)
            except Exception as e:
                logger.error(f"[{project_id}] Tool execution error: {e}")
                messages.append(ToolMessage(
                    tool_call_id=tc["id"],
                    content=f"Error executing tool: {str(e)}",
                ))
    
    send_terminal_message(project_id, f"⚠️ App error fixer for {component_name} completed without explicit fix signal.\n\r")
    return {"fixed": False, "summary": "Agent completed without signaling fix"}
