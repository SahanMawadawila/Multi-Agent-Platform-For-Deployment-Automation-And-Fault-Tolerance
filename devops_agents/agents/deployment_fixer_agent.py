from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import InjectedState, ToolNode
from pydantic import BaseModel, Field
from tools.git_tools import AsyncGitTools
from app.kafka_terminal_producer import send_terminal_message
from config.settings import settings
from typing import Annotated, List, Optional
import os
import subprocess

# ============== TOOLS ==============
@tool
async def read_file_structure(state: Annotated[dict, InjectedState]) -> str:
    """Returns the current list of files in the GitOps repository."""
    gitops_dir = state["gitops_dir"] + "_push"
    files = await AsyncGitTools.list_files(gitops_dir)
    return "\n".join(files)

@tool
async def read_file(
    file_path: str,
    state: Annotated[dict, InjectedState]
) -> str:
    """Reads a file from the GitOps repository."""
    gitops_dir = state["gitops_dir"] + "_push"
    project_id = state.get("project_id", "")
    send_terminal_message(project_id, f"📖 Reading {file_path} in GitOps repo\n\r")
    return await AsyncGitTools.read_file(gitops_dir, file_path)

@tool
async def write_file(
    file_path: str,
    content: str,
    state: Annotated[dict, InjectedState]
) -> str:
    """Writes content to a file in the GitOps repository."""
    gitops_dir = state["gitops_dir"] + "_push"
    project_id = state.get("project_id", "")
    
    full_path = os.path.join(gitops_dir, file_path)
    os.makedirs(os.path.dirname(full_path) if os.path.dirname(full_path) else ".", exist_ok=True)
    
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    send_terminal_message(project_id, f"✏️ Updated {file_path} in GitOps repo\n\r")
    return f"Successfully wrote to {file_path}"

@tool
async def commit_and_push(
    commit_message: str,
    state: Annotated[dict, InjectedState]
) -> str:
    """Commits and pushes all changes to the GitOps repository."""
    gitops_dir = state["gitops_dir"] + "_push"
    project_id = state.get("project_id", "")
    
    send_terminal_message(project_id, "📤 Pushing fixes to GitOps repository...\n\r")
    
    try:
        subprocess.run(["git", "add", "."], cwd=gitops_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", commit_message], cwd=gitops_dir, check=True, capture_output=True)
        subprocess.run(["git", "push"], cwd=gitops_dir, check=True, capture_output=True)
        
        # Force ArgoCD to sync immediately
        send_terminal_message(project_id, "🔄 Triggering ArgoCD sync...\n\r")
        app_name = f"app-{project_id}"
        subprocess.run(
            ["kubectl", "annotate", "application", app_name, "-n", "argocd", "argocd.argoproj.io/refresh=hard", "--overwrite"],
            check=False, capture_output=True
        )
        return "Successfully committed and pushed changes"
    except subprocess.CalledProcessError as e:
        return f"Error pushing changes: {e.stderr.decode() if e.stderr else str(e)}"

@tool
async def execute_k8s_command(
    command: str,
    state: Annotated[dict, InjectedState]
) -> str:
    """Executes a kubectl command to get pod details or logs from the Kubernetes cluster.
    Only read-only commands like 'kubectl get pods', 'kubectl describe pod <pod_name>', or 'kubectl logs <pod_name>' are permitted."""
    project_id = state.get("project_id", "")
    send_terminal_message(project_id, f"🔍 Executing k8s command: {command}\n\r")
    
    if not command.strip().startswith("kubectl"):
        return "Error: Only 'kubectl' commands are allowed."
        
    forbidden_words = ["delete", "apply", "create", "edit", "scale", "exec", "replace", "patch"]
    if any(word in command.split() for word in forbidden_words):
        return "Error: Only read-only commands (get, describe, logs) are allowed."
        
    try:
        result = subprocess.run(command.split(), check=True, capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error executing command: {e.stderr}"

class DeploymentFixComplete(BaseModel):
    """Signal that the agent has finished investigating and applying fixes."""
    is_app_issue: bool = Field(..., description="Set to True if this is an application code issue that cannot be fixed in GitOps. False if it was a GitOps config issue that you fixed.")
    error: str = Field(..., description="Reason for the error")
    fix_applied: Optional[str] = Field(None, description="Description of the fix applied (optional if it's an app issue)")

tools = [read_file_structure, read_file, write_file, commit_and_push, execute_k8s_command, DeploymentFixComplete]

# ============== AGENTS ==============

DEPLOYMENT_FIXER_PROMPT = """You are an expert Kubernetes GitOps engineer. A deployment has failed or crashed.
Your job is to investigate the issue using the provided logs and the GitOps repository, and fix it if it is a GitOps configuration issue.

Follow this Chain of Thought process:
1. IDENTIFY: Read the provided deployment error logs. Determine if this is an Application Code Issue or a GitOps Issue.
   - Application Code Issue: The application panics, throws unhandled exceptions, lacks required environment variables that must be added to the code, or has logic errors. YOU CANNOT FIX THIS.
   - GitOps Issue: The container is CrashLoopBackOff due to a missing ConfigMap, bad environment variable value in the manifest, wrong image tag, missing secret, or malformed YAML. YOU CAN FIX THIS.
2. THINK: Use `execute_k8s_command` to get pod details/logs if needed. If it's a GitOps issue, use `read_file_structure` and `read_file` to find the incorrect manifests in the GitOps repo. Think step-by-step on how to fix them.
3. FIX: If it's a GitOps issue, use `write_file` to correct the manifests. If it's an Application Code issue, SKIP to COMPLETE.
4. PUSH: If you made changes, use `commit_and_push` to apply the GitOps fixes.
5. COMPLETE: Call `DeploymentFixComplete` with `is_app_issue` set appropriately, `error` (reason for error), and `fix_applied` (what you changed, optional if it's an app issue).
"""

async def deployment_fixer_agent(state):
    """Executes the CoT deployment fix."""
    project_id = state.get("project_id", "")
    deployment_fixing_messages = state.get("deployment_fixing_messages", [])
    error_logs = state.get("deployment_error_logs", "No logs")
    
    llm = ChatOpenAI(model="o4-mini", api_key=settings.openai_key)
    llm_with_tools = llm.bind_tools(tools)
    
    if not deployment_fixing_messages:
        # First failure
        send_terminal_message(project_id, "🛠️ Analyzing deployment failure...\n\r")
        initial_human = HumanMessage(content=f"The deployment failed with these logs:\n\n{error_logs}\n\nPlease analyze and fix it if it's a GitOps issue.")
        llm_messages = [
            SystemMessage(content=DEPLOYMENT_FIXER_PROMPT),
            initial_human
        ]
        response = await llm_with_tools.ainvoke(llm_messages)
        return {"deployment_fixing_messages": [initial_human, response]}
    else:
        last_message = deployment_fixing_messages[-1]
        
        is_new_failure = False
        if isinstance(last_message, ToolMessage) and last_message.content.startswith("Task 'DeploymentFixComplete' acknowledged"):
            is_new_failure = True
            
        llm_messages = [SystemMessage(content=DEPLOYMENT_FIXER_PROMPT)] + deployment_fixing_messages
        
        if is_new_failure:
            send_terminal_message(project_id, "⚠️ Previous deployment fix failed. Analyzing new error...\n\r")
            new_human = HumanMessage(content=f"Your previous fix was applied, but the deployment failed AGAIN with this NEW error:\n\n{error_logs}\n\nPlease rethink your approach.")
            llm_messages.append(new_human)
            response = await llm_with_tools.ainvoke(llm_messages)
            return {"deployment_fixing_messages": [new_human, response]}
        else:
            response = await llm_with_tools.ainvoke(llm_messages)
            return {"deployment_fixing_messages": [response]}

# ============== GRAPH HELPERS ==============
async def deployment_fixer_tool_node(state):
    """Execute tools with state injection."""
    state_copy = dict(state)
    state_copy["messages"] = state.get("deployment_fixing_messages", [])
    node = ToolNode(tools)
    result = await node.ainvoke(state_copy)
    return {"deployment_fixing_messages": result.get("messages", [])}

def check_deployment_fix_complete(state):
    """Route based on agent output."""
    deployment_fixing_messages = state.get("deployment_fixing_messages", [])
    if not deployment_fixing_messages:
        return "deployment_fixer_agent"
    
    last_message = deployment_fixing_messages[-1]
    
    if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
        tool_name = last_message.tool_calls[0]["name"]
        if tool_name == "DeploymentFixComplete":
            return "fix_complete"
        return "deployment_fixer_tool"
    
    return "deployment_fixer_agent"

def finalize_deployment_fix(state):
    """Mark fix as complete and route to retry or fail."""
    project_id = state.get("project_id", "")
    retry_count = state.get("retry_count", 0)
    deployment_fixing_messages = state.get("deployment_fixing_messages", [])
    
    new_messages = []
    is_app_issue = False
    
    if deployment_fixing_messages:
        last_msg = deployment_fixing_messages[-1]
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            for tc in last_msg.tool_calls:
                if tc["name"] == "DeploymentFixComplete":
                    is_app_issue = tc["args"].get("is_app_issue", False)
                    error = tc["args"].get("error", "Unknown error")
                    fix_applied = tc["args"].get("fix_applied", "No fix applied")
                    
                    if is_app_issue:
                        send_terminal_message(project_id, f"❌ Unfixable Application Code Issue Detected. Error: {error}\n\r")
                    else:
                        send_terminal_message(project_id, f"✅ GitOps Fix applied. Error was: {error}. Fix: {fix_applied}. Retrying deployment...\n\r")
                        
                new_messages.append(ToolMessage(
                    tool_call_id=tc["id"],
                    content=f"Task 'DeploymentFixComplete' acknowledged."
                ))

    return {
        "retry_count": retry_count + 1,
        "deployment_fixing_messages": new_messages,
        "is_app_issue": is_app_issue,
        "deployment_status": "retrying" if not is_app_issue else "failed"
    }
