# agents/repo_analyst.py
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, AIMessage # <--- Changed import
from state import RepoAnalysisOutput
from tools.git_tools import AsyncGitTools
from typing import Annotated, Optional
import json
import uuid # <--- Import UUID for unique tool call IDs

# Store local_path globally for the tool to access
_current_local_path: str = ""

def set_local_path(path: str):
    """Set the local path for tools to use."""
    global _current_local_path
    _current_local_path = path

@tool
async def read_repo_file(file_path: str) -> str:
    """Reads a file from the checked-out repository."""
    global _current_local_path
    if not _current_local_path:
        return "Error: Internal path configuration missing."
    return await AsyncGitTools.read_file(_current_local_path, file_path)

tools = [read_repo_file, RepoAnalysisOutput]

# --- REMOVED THE CUSTOM _ToolCallMessage CLASS ---

async def repo_analysis_agent(state):
    """Programmatic repo analyzer that reads common files and returns structured output."""
    current_count = state.get("loop_count", 0)
    if current_count > 5:
        # Use SystemMessage for errors
        return {"messages": [SystemMessage(content="ERROR: Loop limit reached.")], "loop_count": current_count}

    local_path = state.get("local_path")
    if not local_path:
        return {"messages": [SystemMessage(content="ERROR: local_path not set")], "loop_count": current_count}

    # Helper to attempt to read a file and return None if not found
    async def _maybe_read(relpath: str) -> Optional[str]:
        res = await AsyncGitTools.read_file(local_path, relpath)
        if res.startswith("File not found") or res.startswith("Error reading file"):
            return None
        return res

    # 1. Gather Context (Same as before)
    package_json_raw = await _maybe_read("package.json")
    tsconfig_raw = await _maybe_read("tsconfig.json")
    env_example_raw = await _maybe_read(".env.example")
    package_lock_raw = await _maybe_read("package-lock.json")
    yarn_lock_raw = await _maybe_read("yarn.lock")
    pnpm_lock_raw = await _maybe_read("pnpm-lock.yaml")

    # Defaults
    language = "node"
    version = "18"
    package_manager = "npm"
    port = 8080
    build_command = ""
    run_command = ""
    env_vars = []
    env_defaults = {}
    uses_typescript = False
    lockfile = None
    build_output = "dist"
    start_script = None
    detected_ports = []
    has_native = False
    build_tools = []
    repo_name = "app"
    framework = "express" # Default fallback

    # 2. Logic (Same as before)
    if package_json_raw:
        try:
            pj = json.loads(package_json_raw)
            scripts = pj.get("scripts", {})
            build_command = scripts.get("build", "")
            run_command = scripts.get("start", "") or run_command
            deps = {**pj.get("dependencies", {}), **pj.get("devDependencies", {})}
            
            if "typescript" in deps or tsconfig_raw:
                uses_typescript = True
            
            # Framework detection
            if "next" in deps:
                detected_ports.append(3000)
                framework = "next"
            elif "nest" in deps:
                framework = "nest"
            else:
                detected_ports.append(3000) # Default express/node often 3000 or 8080

            repo_name = pj.get("name", repo_name)
            main_entry = pj.get("main")
            if main_entry and not start_script:
                start_script = main_entry
        except Exception:
            pass

    if pnpm_lock_raw:
        lockfile = "pnpm-lock.yaml"
        package_manager = "pnpm"
    elif yarn_lock_raw:
        lockfile = "yarn.lock"
        package_manager = "yarn"
    elif package_lock_raw:
        lockfile = "package-lock.json"
        package_manager = "npm"

    if tsconfig_raw:
        try:
            ts = json.loads(tsconfig_raw)
            compiler = ts.get("compilerOptions", {})
            outdir = compiler.get("outDir")
            if outdir:
                build_output = outdir
        except Exception:
            pass

    if env_example_raw:
        for line in env_example_raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env_vars.append(k.strip())

    # 3. Construct Output Args
    output_args = {
        "language": language,
        "version": version,
        "package_manager": package_manager,
        "port": detected_ports[0] if detected_ports else port,
        "build_command": build_command,
        "run_command": run_command or start_script or "npm start",
        "env_variables": env_vars,
        "has_lockfile": bool(lockfile),
        "framework": framework
    }

    # --- FIX: Return a standard AIMessage with tool_calls ---
    # LangGraph expects standard message objects. We create an AIMessage
    # that "pretends" the AI decided to call the RepoAnalysisOutput tool.
    
    msg = AIMessage(
        content="",
        tool_calls=[{
            "name": "RepoAnalysisOutput",
            "args": output_args,
            "id": str(uuid.uuid4()) # Unique ID required for tool calls
        }]
    )
    
    return {"messages": [msg], "loop_count": current_count + 1}