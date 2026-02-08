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

# Schema for planning
class FixStep(BaseModel):
    id: int = Field(..., description="Progressive step number starting from 1")
    task: str = Field(..., description="Description of the fix task (e.g., 'Update Dockerfile to use node:18')")

class FixPlan(BaseModel):
    explanation: str = Field(..., description="High-level explanation of why the build failed and how the steps fix it")
    steps: List[FixStep] = Field(..., description="Ordered list of steps to resolve the issue")

# Schema for completion signal
class FixComplete(BaseModel):
    """Signal that the current planned step has been applied and pushed."""
    summary: str = Field(..., description="Brief summary of what was fixed in this specific step")

tools = [read_file_structure, read_file, write_file, commit_and_push, FixComplete]

# ============== AGENTS ==============

ANALYZER_PROMPT = """You are a DevOps analysis expert. Your job is to investigate a CI/CD build failure.

1. Review the error logs provided.
2. Use `read_file_structure` and `read_file` to understand the codebase.
3. Identify exactly why the build failed.
4. Provide a clear, technical summary of the root cause.

You are NOT allowed to do changes to the codebase, unless it is a Dockerfile, config files or build scripts like yml files.
Do NOT attempt to fix it. Just analyze and report your findings.
"""

async def error_analyzer_agent(state):
    """Analyzes build errors without making changes."""
    project_id = state.get("project_id", "")
    error_logs = state.get("build_error_logs", "No logs")
    
    send_terminal_message(project_id, "🔍 Analyzing root cause of build failure...\n\r")
    
    llm = ChatOpenAI(model="gpt-5.1", api_key=settings.openai_key, temperature=0)
    llm_with_tools = llm.bind_tools([read_file_structure, read_file])
    
    messages = [
        SystemMessage(content=ANALYZER_PROMPT),
        HumanMessage(content=f"Build failed with error:\n\n{error_logs}")
    ]
    
    # Simple loop for analysis
    for i in range(5):
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)
        
        # Exit Condition: LLM provides a summary (text content) and no more tools
        if not response.tool_calls and response.content:
            return {"analysis_results": response.content}
        
        # fallback if it returns nothing
        if not response.tool_calls and not response.content:
            print("Analyzer returned empty response, retrying...")
            continue

        # Execute tools
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            print(f"Tool call: {tool_name} with args {tool_args}")
            
            if tool_name == "read_file_structure":
                result = await read_file_structure.ainvoke({"state": state})
            elif tool_name == "read_file":
                result = await read_file.ainvoke({**tool_args, "state": state})
            else:
                result = f"Error: Tool {tool_name} not allowed for analyzer."
            
            messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
            
    print("Analysis did not reach conclusion within tool call limit.")
    return {"analysis_results": "Analysis timed out or failed to reach conclusion."}

PLANNER_PROMPT = """You are a DevOps architect. Based on the analysis of a build failure, create a step-by-step resolution plan.

Each step should be small and verifiable. For example:
- Step 1: Update Dockerfile to fix syntax error in RUN command.
- Step 2: Add missing 'express' dependency to package.json.

Do not suggest more than 3 steps. Each step MUST be actionable by a code-writing agent.
"""

async def error_planner_agent(state):
    """Creates a structured plan based on analysis."""
    project_id = state.get("project_id", "")
    analysis = state.get("analysis_results", "No analysis")
    
    send_terminal_message(project_id, "📋 Creating fix plan...\n\r")
    
    llm = ChatOpenAI(model="gpt-5.1", api_key=settings.openai_key, temperature=0)
    structured_llm = llm.with_structured_output(FixPlan)
    
    plan = await structured_llm.ainvoke([
        SystemMessage(content=PLANNER_PROMPT),
        HumanMessage(content=f"Analysis of failure:\n{analysis}")
    ])
    
    # Store plan as plain dicts for state serialization
    plan_dicts = [{"id": s.id, "task": s.task, "status": "not-started"} for s in plan.steps]
    
    msg = f"Plan created: {plan.explanation}\n\r"
    for s in plan.steps:
        msg += f" - Step {s.id}: {s.task}\n\r"
    send_terminal_message(project_id, msg)
    
    return {
        "error_fixing_plan": plan_dicts,
        "current_step_index": 0
    }

EXECUTOR_PROMPT = """You are a DevOps engineer executing a specific fix step.

Current Task: {task}
Full Plan Context: {plan_explanation}

Rules:
1. ONLY perform the task described in the 'Current Task'.
2. Use `write_file` to implement the change.
3. Use `commit_and_push` to submit the fix.
4. ALWAYS call `FixComplete` with a summary once you have pushed your change.
"""

async def error_fixing_agent(state):
    """Executes ONE step of the plan."""
    project_id = state.get("project_id", "")
    plan = state.get("error_fixing_plan", [])
    step_idx = state.get("current_step_index", 0)
    error_fixing_messages = state.get("error_fixing_messages", [])
    
    if step_idx >= len(plan):
        return {"build_status": "plan_exhausted"}
    
    current_step = plan[step_idx]
    
    if not error_fixing_messages:
        send_terminal_message(project_id, f"🛠️ Executing Step {current_step['id']}: {current_step['task']}...\n\r")

    llm = ChatOpenAI(model="gpt-5-mini", api_key=settings.openai_key, temperature=0)
    llm_with_tools = llm.bind_tools(tools)
    
    system_content = EXECUTOR_PROMPT.format(
        task=current_step['task'],
        plan_explanation="Multiple steps to resolve build failure."
    )
    
    if not error_fixing_messages:
        initial_human = HumanMessage(content=f"Please carry out this specific task: {current_step['task']}")
        llm_messages = [
            SystemMessage(content=system_content),
            initial_human
        ]
        response = await llm_with_tools.ainvoke(llm_messages)
        return {"error_fixing_messages": [initial_human, response]}
    else:
        llm_messages = [SystemMessage(content=system_content)] + error_fixing_messages
        response = await llm_with_tools.ainvoke(llm_messages)
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
    """Mark current step as complete and transition to rebuild."""
    project_id = state.get("project_id", "")
    step_idx = state.get("current_step_index", 0)
    plan = state.get("error_fixing_plan", [])
    retry_count = state.get("retry_count", 0)
    error_fixing_messages = state.get("error_fixing_messages", [])
    
    send_terminal_message(project_id, f"✅ Step {step_idx + 1} applied. Verifying with build...\n\r")
    
    # 1. Provide ToolMessage responses for any pending tool calls (like FixComplete)
    # to satisfy OpenAI's requirement that all tool calls must have a response.
    new_messages = []
    if error_fixing_messages:
        last_msg = error_fixing_messages[-1]
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            for tc in last_msg.tool_calls:
                new_messages.append(ToolMessage(
                    tool_call_id=tc["id"],
                    content=f"Task '{tc['name']}' acknowledged and step finalized."
                ))

    # We update the status in the plan list
    if plan and step_idx < len(plan):
        plan_copy = [dict(s) for s in plan]
        plan_copy[step_idx]["status"] = "completed"
    else:
        plan_copy = plan

    return {
        "retry_count": retry_count + 1,
        "current_step_index": step_idx + 1,
        "error_fixing_plan": plan_copy,
        "build_status": "retrying",
        "error_fixing_messages": new_messages  # This now appends the required ToolMessages
    }
