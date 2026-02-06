from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import InjectedState, ToolNode
from pydantic import BaseModel, Field
from tools.git_tools import AsyncGitTools
from app.kafka_terminal_producer import send_terminal_message
from config.settings import settings
from typing import Annotated, List
import os

# ============== TOOLS ==============
@tool
async def read_file_structure(state: Annotated[dict, InjectedState]) -> str:
    """Returns the current list of files in the repository (fresh from filesystem)."""
    local_path = state["local_path"]
    # Get fresh file list from filesystem
    files = await AsyncGitTools.list_files(local_path)
    return "\n".join(files)

@tool
async def read_file(
    file_path: str,
    state: Annotated[dict, InjectedState]
) -> str:
    """Reads a file from the repository.
    
    Args:
        file_path: Relative path to the file (e.g., 'Dockerfile', 'package.json')
    """
    local_path = state["local_path"]
    project_id = state.get("project_id", "")
    send_terminal_message(project_id, f"📖 Reading {file_path}\n\r")
    return await AsyncGitTools.read_file(local_path, file_path)

@tool
async def write_file(
    file_path: str,
    content: str,
    state: Annotated[dict, InjectedState]
) -> str:
    """Writes content to a file in the repository.
    
    Args:
        file_path: Relative path to the file (e.g., 'Dockerfile')
        content: The content to write to the file
    """
    local_path = state["local_path"]
    project_id = state.get("project_id", "")
    
    full_path = os.path.join(local_path, file_path)
    os.makedirs(os.path.dirname(full_path) if os.path.dirname(full_path) else ".", exist_ok=True)
    
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    send_terminal_message(project_id, f"✏️ Updated {file_path}\n\r")
    return f"Successfully wrote to {file_path}"

@tool
async def commit_and_push(
    commit_message: str,
    state: Annotated[dict, InjectedState]
) -> str:
    """Commits and pushes all changes to the repository.
    
    Args:
        commit_message: The commit message for the changes
    """
    local_path = state["local_path"]
    project_id = state.get("project_id", "")
    
    send_terminal_message(project_id, "📤 Pushing fixes to repository...\n\r")
    
    import subprocess
    try:
        subprocess.run(["git", "add", "."], cwd=local_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", commit_message], cwd=local_path, check=True, capture_output=True)
        subprocess.run(["git", "push"], cwd=local_path, check=True, capture_output=True)
        return "Successfully committed and pushed changes"
    except subprocess.CalledProcessError as e:
        return f"Error pushing changes: {e.stderr.decode() if e.stderr else str(e)}"

# Schema for completion signal
class FixComplete(BaseModel):
    """Signal that the fix has been applied and pushed."""
    summary: str = Field(..., description="Brief summary of what was fixed")

tools = [read_file_structure, read_file, write_file, commit_and_push, FixComplete]

# ============== AGENT ==============
SYSTEM_PROMPT = """You are a DevOps debugging expert. A CI/CD build has failed and you need to fix it.

## Your Task:
1. Analyze the error message provided
2. Read relevant files to understand the issue
3. Fix the problematic file(s)
4. Commit and push the fix
5. Call FixComplete when done

## Common Issues and Fixes:
- **Dockerfile syntax errors**: Check FROM, RUN, COPY, CMD statements
- **Missing dependencies**: Check package.json or requirements.txt
- **Port mismatch**: Ensure EXPOSE matches application port
- **Build command errors**: Verify build scripts exist
- **Permission issues**: Check file permissions in Dockerfile

## Available Tools:
- read_file_structure: See all files in the repo
- read_file: Read any file content
- write_file: Write/update a file
- commit_and_push: Commit and push changes
- FixComplete: Signal that fix is complete

## Rules:
- Be precise with fixes - only change what's necessary
- Always commit and push after making changes
- Call FixComplete with a summary when done
"""

async def error_fixing_agent(state):
    """LLM-powered agent that analyzes build errors and fixes them."""
    
    project_id = state.get("project_id", "")
    error_fixing_messages = state.get("error_fixing_messages", [])
    error_logs = state.get("build_error_logs", "No error logs available")
    retry_count = state.get("retry_count", 0)
    
    # First run for this error fix attempt
    if not error_fixing_messages:
        send_terminal_message(project_id, f"🔧 Analyzing build failure (Attempt {retry_count + 1}/3)...\n\r")
    
    # Build LLM
    llm = ChatOpenAI(
        model="gpt-5-mini",
        api_key=settings.openai_key,
        temperature=0
    )
    llm_with_tools = llm.bind_tools(tools)
    
    # Build messages for LLM
    if not error_fixing_messages:
        # First call - include error context
        llm_messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"""The build has failed with the following error:

{error_logs}

Please analyze this error, read the relevant files, fix the issue, and push the changes.""")
        ]
    else:
        # Subsequent calls - continue conversation
        llm_messages = [SystemMessage(content=SYSTEM_PROMPT)] + error_fixing_messages
    
    response = await llm_with_tools.ainvoke(llm_messages)
    
    # Return to separate message field for error fixing agent
    return {"error_fixing_messages": [response]}

# ============== GRAPH HELPERS ==============
async def error_fixing_tool_node(state):
    """Execute tools with state injection."""
    # We need to temporarily put error_fixing_messages into messages for ToolNode
    state_copy = dict(state)
    state_copy["messages"] = state.get("error_fixing_messages", [])
    node = ToolNode(tools)
    result = await node.ainvoke(state_copy)
    # Map back to error_fixing_messages
    return {"error_fixing_messages": result.get("messages", [])}

def check_fix_complete(state):
    """Route based on agent output."""
    error_fixing_messages = state.get("error_fixing_messages", [])
    if not error_fixing_messages:
        return "error_fixing_agent"
    
    last_message = error_fixing_messages[-1]
    
    if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
        tool_name = last_message.tool_calls[0]["name"]
        if tool_name == "FixComplete":
            return "fix_complete"
        return "error_fixing_tool"
    
    return "error_fixing_agent"

def finalize_fix(state):
    """Mark fix as complete and increment retry count."""
    project_id = state.get("project_id", "")
    retry_count = state.get("retry_count", 0)
    
    send_terminal_message(project_id, "✅ Fix applied. Rebuilding...\n\r")
    
    return {
        "retry_count": retry_count + 1,
        "build_status": "retrying",
        "error_fixing_messages": []  # Clear for next attempt if needed
    }
