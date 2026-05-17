from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
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
        file_path: Relative path to the file (e.g., 'package.json', 'project.toml')
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
        file_path: Relative path to the file (e.g., 'package.json')
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
    """Signal that the fix has been applied and pushed. ALWAYS call this when you are done."""
    summary: str = Field(..., description="Brief summary of what was fixed")

tools = [read_file_structure, read_file, write_file, commit_and_push, FixComplete]

# ============== AGENTS ==============

ERROR_FIXING_PROMPT = """You are an expert DevOps and Software Engineer. A CI/CD build has failed. Your job is to fix it.
Follow this Chain of Thought process:
1. IDENTIFY: Read the provided error logs. If needed, use `read_file_structure` and `read_file` to inspect the code.
2. THINK: Think step-by-step about what caused the error and how to solve it.
3. FIX: Use `write_file` to apply the necessary code changes (e.g., fix dependencies in package.json/pom.xml, fix build scripts, or application code). Note: We use Cloud Native Buildpacks, so there is NO Dockerfile to update.
4. PUSH: Use `commit_and_push` to save and deploy your fix.
5. COMPLETE: Call `FixComplete` to end your workflow.
"""

async def error_fixing_agent(state):
    """Executes the CoT fix."""
    project_id = state.get("project_id", "")
    error_fixing_messages = state.get("error_fixing_messages", [])
    error_logs = state.get("build_error_logs", "No logs")
    
    component = state.get("component") or {}
    component_name = component.get("name")
    
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.openai_key)
    llm_with_tools = llm.bind_tools(tools)
    
    if not error_fixing_messages:
        # First failure
        send_terminal_message(project_id, "🛠️ Analyzing and fixing build failure...\n\r", component_name)
        initial_human = HumanMessage(content=f"The build failed with this error:\n\n{error_logs}\n\nPlease analyze and fix it.")
        llm_messages = [
            SystemMessage(content=ERROR_FIXING_PROMPT),
            initial_human
        ]
        response = await llm_with_tools.ainvoke(llm_messages)
        return {"error_fixing_messages": [initial_human, response]}
    else:
        # Subsequent tool execution OR a brand new failure after a previous fix attempt
        last_message = error_fixing_messages[-1]
        
        is_new_failure = False
        if isinstance(last_message, ToolMessage) and last_message.content.startswith("Task 'FixComplete' acknowledged"):
            is_new_failure = True
            
        llm_messages = [SystemMessage(content=ERROR_FIXING_PROMPT)] + error_fixing_messages
        
        if is_new_failure:
            send_terminal_message(project_id, "⚠️ Previous fix failed. Analyzing new error...\n\r", component_name)
            new_human = HumanMessage(content=f"Your previous fix was applied, but the build failed AGAIN with this NEW error:\n\n{error_logs}\n\nPlease rethink your approach and fix this new issue.")
            llm_messages.append(new_human)
            response = await llm_with_tools.ainvoke(llm_messages)
            return {"error_fixing_messages": [new_human, response]}
        else:
            # Just continuing the current reasoning loop (e.g. after reading a file)
            appended_messages = []
            if not getattr(last_message, "tool_calls", None):
                reminder = HumanMessage(content="You must use a tool to proceed. Use tools to read files, write, or commit. If you are finished, invoke the 'FixComplete' tool.")
                llm_messages.append(reminder)
                appended_messages.append(reminder)
            
            response = await llm_with_tools.ainvoke(llm_messages)
            appended_messages.append(response)
            
            return {"error_fixing_messages": appended_messages}

# ============== GRAPH HELPERS ==============
async def error_fixing_tool_node(state):
    """Execute tools with state injection."""
    state_copy = dict(state)
    state_copy["messages"] = state.get("error_fixing_messages", [])
    node = ToolNode(tools)
    result = await node.ainvoke(state_copy)
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
    """Mark fix as complete and transition to rebuild."""
    project_id = state.get("project_id", "")
    retry_count = state.get("retry_count", 0)
    error_fixing_messages = state.get("error_fixing_messages", [])
    
    component = state.get("component") or {}
    component_name = component.get("name")
    
    send_terminal_message(project_id, f"✅ Fix applied. Verifying with build (Attempt {retry_count + 1})...\n\r", component_name)
    
    new_messages = []
    if error_fixing_messages:
        last_msg = error_fixing_messages[-1]
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            for tc in last_msg.tool_calls:
                new_messages.append(ToolMessage(
                    tool_call_id=tc["id"],
                    content=f"Task 'FixComplete' acknowledged and step finalized."
                ))

    return {
        "retry_count": retry_count + 1,
        "build_status": "retrying",
        "error_fixing_messages": new_messages  
    }
