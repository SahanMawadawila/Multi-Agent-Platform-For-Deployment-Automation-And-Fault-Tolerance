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
import re
import subprocess
import logging

logger = logging.getLogger("error_fixing_agent")

# Patterns that indicate a transient/infrastructure error (not a code issue).
# When matched, we skip the LLM fix loop and just retry the build.
TRANSIENT_ERROR_PATTERNS = [
    r"unable to get dependency",
    r"unable to invoke layer creator",
    r"Downloading from https?://.*\.(tar\.gz|zip)",
    r"Failed to connect to",
    r"Connection timed out",
    r"Connection reset",
    r"502 Bad Gateway",
    r"503 Service Unavailable",
    r"rate limit",
    r"ETIMEDOUT",
    r"ECONNRESET",
    r"socket hang up",
    r"no space left on device",
    r"runner.*terminated",
    r"The runner has received a shutdown signal",
]

def is_transient_error(error_logs: str) -> bool:
    """Check if the build error is a transient infrastructure issue, not a code bug."""
    if not error_logs:
        return False
    for pattern in TRANSIENT_ERROR_PATTERNS:
        if re.search(pattern, error_logs, re.IGNORECASE):
            return True
    return False

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

ERROR_FIXING_PROMPT = """You are an expert DevOps and Software Engineer specializing in Cloud Native Buildpacks and GitHub Actions CI/CD.

A CI/CD build has failed. The build uses **Cloud Native Buildpacks** (via `pack build`) inside a GitHub Actions workflow — there are NO Dockerfiles.

## Error Classification
First, classify the error into one of these categories:

### Category 1: Buildpack / Pipeline Configuration Error
The workflow YAML (`.github/workflows/ci-*.yml`) has wrong `pack build` flags.
Examples:
- Wrong `--builder` image (e.g., using `builder-jammy-base` when `builder-jammy-full` is needed for frontend/NGINX)
- Missing or wrong `--env` flags (e.g., `BP_WEB_SERVER=nginx`, `BP_NODE_PROJECT_PATH`, `BP_MAVEN_BUILT_MODULE`, `BP_JVM_VERSION`)
- Wrong `--path` (pointing to wrong directory in a monorepo)
- Wrong `BP_WEB_SERVER_ROOT` (e.g., `dist` vs `build` depending on the framework)
**Fix**: Edit the workflow file at `.github/workflows/ci-*.yml` using `write_file`.

### Category 2: Application Source Code / Dependency Error  
The app code or config is broken — buildpacks detected it correctly but the code itself is wrong.
Examples:
- Missing dependency in `package.json`, `pom.xml`, `requirements.txt`, `go.mod`
- Syntax error or import error in source code
- Missing `Procfile` when buildpacks can't auto-detect the start command
- Wrong `start` script in `package.json`
- Missing or broken build script (e.g., `npm run build` fails)
- Incompatible dependency versions
**Fix**: Edit the application source files using `write_file`.

## Chain of Thought Process
1. **READ THE ERROR LOGS** carefully. The workflow YAML is provided below the logs — study the `pack build` command, its `--path`, `--env` flags, and `--builder`.
2. **CLASSIFY** the error into Category 1 or 2 above.
3. **INVESTIGATE** if needed: use `read_file_structure` and `read_file` to inspect the repository.
4. **FIX** using `write_file`:
   - For Category 1: edit `.github/workflows/ci-*.yml`
   - For Category 2: edit the application source files
5. **PUSH** using `commit_and_push`.
6. **COMPLETE** by calling `FixComplete`.

## CRITICAL RULES
- **NEVER create a Dockerfile.** This project uses Cloud Native Buildpacks exclusively.
- **NEVER remove the `pack build` step** or replace it with `docker build`.
- When editing the workflow YAML, preserve the overall structure — only change the specific flags/env vars that are wrong.
- If the error mentions a missing buildpack (e.g., "no valid buildpacks"), the `--builder` or `--path` is likely wrong.
- If the error mentions "unable to find" a file or module, check if `--path` or `BP_NODE_PROJECT_PATH`/`BP_MAVEN_BUILT_MODULE` is correct.
- For frontend apps that produce static files (React, Vue, Angular, Vite), the builder must be `paketobuildpacks/builder-jammy-full` and `BP_WEB_SERVER=nginx` must be set.
- `BP_WEB_SERVER_ROOT` should match the framework's output directory (`dist` for Vite/Vue, `build` for Create React App, `out` for Next.js static export).
"""

async def error_fixing_agent(state):
    """Executes the CoT fix."""
    project_id = state.get("project_id", "")
    error_fixing_messages = state.get("error_fixing_messages", [])
    error_logs = state.get("build_error_logs", "No logs")
    
    component = state.get("component") or {}
    component_name = component.get("name")
    
    # Check for transient errors — skip LLM entirely and just retry
    if not error_fixing_messages and is_transient_error(error_logs):
        send_terminal_message(
            project_id,
            "🔄 Transient build error detected (network/runner issue). Retrying without code changes...\n\r",
            component_name,
        )
        logger.info(f"[{project_id}] Transient error detected, skipping LLM fix loop")
        # Return a FixComplete-like signal so the graph routes to finalize_fix → rebuild
        from langchain_core.messages import AIMessage
        fake_fix = AIMessage(
            content="",
            tool_calls=[{
                "id": "transient_skip",
                "name": "FixComplete",
                "args": {"summary": "Transient infrastructure error (network/runner). Retrying build."},
            }],
        )
        return {"error_fixing_messages": [fake_fix]}
    
    llm = ChatOpenAI(model="o4-mini", api_key=settings.openai_key)
    llm_with_tools = llm.bind_tools(tools)
    
    if not error_fixing_messages:
        # First failure — inject workflow file content for full context
        send_terminal_message(project_id, "🛠️ Analyzing and fixing build failure...\n\r", component_name)
        
        # Auto-read the workflow file so the LLM can see the pack build command
        workflow_context = ""
        local_path = state.get("local_path", "")
        if local_path:
            workflow_name = f"ci-{component_name}.yml" if component_name else "ci.yml"
            workflow_path = os.path.join(local_path, ".github", "workflows", workflow_name)
            try:
                if os.path.isfile(workflow_path):
                    with open(workflow_path, "r", encoding="utf-8") as wf:
                        workflow_content = wf.read()
                    workflow_context = f"\n\n--- Current Workflow File (.github/workflows/{workflow_name}) ---\n{workflow_content}\n--- End Workflow File ---"
            except Exception as e:
                logger.warning(f"[{project_id}] Could not read workflow file: {e}")
        
        initial_human = HumanMessage(
            content=(
                f"The build failed with this error:\n\n{error_logs}"
                f"{workflow_context}"
                f"\n\nPlease classify this error (pipeline config vs application code) and fix it."
            )
        )
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
            # Check if this new failure is also transient
            if is_transient_error(error_logs):
                send_terminal_message(
                    project_id,
                    "🔄 Transient build error detected again. Retrying...\n\r",
                    component_name,
                )
                from langchain_core.messages import AIMessage
                fake_fix = AIMessage(
                    content="",
                    tool_calls=[{
                        "id": "transient_skip",
                        "name": "FixComplete",
                        "args": {"summary": "Transient infrastructure error. Retrying build."},
                    }],
                )
                return {"error_fixing_messages": [fake_fix]}
            
            send_terminal_message(project_id, "⚠️ Previous fix failed. Analyzing new error...\n\r", component_name)
            new_human = HumanMessage(content=f"Your previous fix was applied, but the build failed AGAIN with this NEW error:\n\n{error_logs}\n\nPlease rethink your approach and fix this new issue.")
            llm_messages.append(new_human)
            response = await llm_with_tools.ainvoke(llm_messages)
            return {"error_fixing_messages": [new_human, response]}
        else:
            # Just continuing the current reasoning loop (e.g. after reading a file)
            response = await llm_with_tools.ainvoke(llm_messages)
            return {"error_fixing_messages": [response]}

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
    """Mark fix as complete and transition to rebuild.
    
    Safety net: force-push any uncommitted changes the LLM may have
    written via write_file but forgot to commit_and_push.
    """
    project_id = state.get("project_id", "")
    retry_count = state.get("retry_count", 0)
    error_fixing_messages = state.get("error_fixing_messages", [])
    local_path = state.get("local_path", "")
    
    component = state.get("component") or {}
    component_name = component.get("name")
    
    # Force-push any uncommitted changes as a safety net.
    # The LLM sometimes writes files but forgets to call commit_and_push.
    if local_path:
        try:
            # Check if there are uncommitted changes
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=local_path, capture_output=True, text=True
            )
            if status.stdout.strip():
                logger.info(f"[{project_id}] Force-pushing uncommitted changes from error fixer")
                send_terminal_message(project_id, "📤 Pushing uncommitted fixes...\n\r", component_name)
                subprocess.run(["git", "add", "."], cwd=local_path, check=True, capture_output=True)
                subprocess.run(
                    ["git", "commit", "-m", "fix: auto-push uncommitted error fixes"],
                    cwd=local_path, check=True, capture_output=True
                )
                subprocess.run(["git", "push"], cwd=local_path, check=True, capture_output=True)
        except Exception as e:
            logger.warning(f"[{project_id}] Force-push failed (may be clean): {e}")
    
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
