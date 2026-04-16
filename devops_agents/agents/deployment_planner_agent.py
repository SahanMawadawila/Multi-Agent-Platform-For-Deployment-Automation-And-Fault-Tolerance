"""
Deployment Planning Agent
A single, powerful agentic loop (like Claude Code) that iteratively explores
a repository using tools and produces a comprehensive DeploymentPlan.

Replaces the old fragmented approach with one agent that decides what to read,
reasons over the repository, and produces the plan.
"""

import os
import logging
from typing import Annotated
from urllib.parse import urlparse, urlunparse

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from agents.plan_schemas import DeploymentPlan, IngressConfig, IngressRule
from agents.planing.component_extractor import run_component_extractor
from agents.planing.infra_extractor import run_infra_extractor
from agents.planing.connection_mapper import run_connection_mapper
from tools.git_tools import AsyncGitTools

# File-based logger for agent traceability (not sent to frontend terminal)
os.makedirs("logs", exist_ok=True)
logger = logging.getLogger("deployment_planner")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    fh = logging.FileHandler("logs/planner_agent.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)


# ============== TOOLS ==============

@tool
async def read_file(
    file_path: str,
    state: Annotated[dict, InjectedState],
    start_line: int = None,
    end_line: int = None
) -> str:
    """Reads a file from the repository, optionally limited to a specific line range.

    Args:
        file_path: Relative path to the file (e.g., 'package.json', 'docker-compose.yml', 'backend/.env')
        start_line: Optional starting line number (1-indexed)
        end_line: Optional ending line number (inclusive)

    Returns:
        The file content as a string, or an error message if not found.
    """
    local_path = state["local_path"]
    project_id = state.get("project_id", "")

    if start_line and end_line:
        logger.info(f"[{project_id}] 📖 Reading {file_path} (Lines {start_line}-{end_line})")
    else:
        logger.info(f"[{project_id}] 📖 Reading {file_path}")
        
    result = await AsyncGitTools.read_file(local_path, file_path, start_line, end_line)
    return result


@tool
async def list_directory(
    directory_path: str,
    state: Annotated[dict, InjectedState]
) -> str:
    """Lists files and directories within a specific directory of the repository.

    Args:
        directory_path: Relative path to the directory (e.g., '.', 'backend', 'services/auth').
                        Use '.' for the repository root.

    Returns:
        A listing of files and directories in the specified path, one per line.
    """
    local_path = state["local_path"]
    project_id = state.get("project_id", "")

    full_path = os.path.join(local_path, directory_path) if directory_path != "." else local_path

    if not os.path.exists(full_path):
        return f"Directory not found: {directory_path}"

    if not os.path.isdir(full_path):
        return f"Not a directory: {directory_path}"

    logger.info(f"[{project_id}] 📂 Listing {directory_path}/")

    ignore_dirs = {".git", "node_modules", "venv", ".venv", "__pycache__",
                   "target", "dist", ".next", "build", ".idea", ".vscode"}

    entries = []
    try:
        for entry in sorted(os.listdir(full_path)):
            if entry in ignore_dirs:
                continue
            entry_path = os.path.join(full_path, entry)
            if os.path.isdir(entry_path):
                entries.append(f"📁 {entry}/")
            else:
                size = os.path.getsize(entry_path)
                entries.append(f"📄 {entry} ({size} bytes)")
    except PermissionError:
        return f"Permission denied: {directory_path}"

    if not entries:
        return f"Directory is empty: {directory_path}"

    return "\n".join(entries)


@tool
async def search_files(
    query: str,
    state: Annotated[dict, InjectedState]
) -> str:
    """Searches for a specific term or regex pattern across all files in the repository.

    Args:
        query: The string or regex pattern to search for (e.g., 'DB_PASSWORD', 'port', 'API_KEY').

    Returns:
        A list of matching files and lines, or a message if no matches found.
    """
    local_path = state["local_path"]
    project_id = state.get("project_id", "")

    logger.info(f"[{project_id}] 🔍 Searching for '{query}'")
    result = await AsyncGitTools.search_files(local_path, query)
    return result


def _build_file_list_str(file_list: list) -> str:
    if len(file_list) > 1500:
        file_list_str = "\n".join(f"- {file}" for file in file_list[:1500])
        file_list_str += f"\n\n... (truncated {len(file_list) - 1500} more files)"
        return file_list_str

    return "\n".join(f"- {file}" for file in file_list)


def _replace_host_in_url(value: str, service_name: str) -> str:
    if not value:
        return service_name

    try:
        parsed = urlparse(value)
        if parsed.scheme and parsed.netloc:
            netloc = parsed.netloc
            userinfo = ""
            hostport = netloc
            if "@" in netloc:
                userinfo, hostport = netloc.rsplit("@", 1)
            host = hostport
            port = ""
            if ":" in hostport:
                host, port = hostport.split(":", 1)
            new_hostport = f"{service_name}:{port}" if port else service_name
            new_netloc = f"{userinfo}@{new_hostport}" if userinfo else new_hostport
            return urlunparse(parsed._replace(netloc=new_netloc))
    except Exception:
        return value.replace("localhost", service_name).replace("127.0.0.1", service_name)

    return value.replace("localhost", service_name).replace("127.0.0.1", service_name)


# ============== AGENT ==============

async def run_deployment_planner(
    file_list: list,
    local_path: str,
    project_id: str,
    build_id: str,
    repo_url: str,
) -> DeploymentPlan:
    """
    Multi-agent planner that extracts components, infra, and connections.

    Args:
        file_list: List of all file paths in the repository
        local_path: Absolute path to the cloned repository
        project_id: Project identifier
        build_id: Build identifier
        repo_url: Repository URL

    Returns:
        DeploymentPlan: The complete deployment plan
    """
    logger.info(f"[{project_id}] 🧠 Starting deployment planning orchestrator...")

    file_list_str = _build_file_list_str(file_list)
    tools = [read_file, list_directory, search_files]

    app_components = await run_component_extractor(
        file_list_str=file_list_str,
        local_path=local_path,
        project_id=project_id,
        repo_url=repo_url,
        tools=tools,
        logger=logger,
    )

    infra_components = await run_infra_extractor(
        file_list_str=file_list_str,
        local_path=local_path,
        project_id=project_id,
        repo_url=repo_url,
        app_components=[component.model_dump() for component in app_components],
        tools=tools,
        logger=logger,
    )

    rename_map = {}
    for infra in infra_components:
        if infra.scope != "project":
            continue
        owner_app = infra.owner_app
        if not owner_app:
            continue
        expected_prefix = f"{owner_app}-"
        if infra.name.startswith(expected_prefix):
            continue
        old_name = infra.name
        infra.name = f"{expected_prefix}{infra.name}"
        rename_map[old_name] = infra.name

    connections = await run_connection_mapper(
        file_list_str=file_list_str,
        local_path=local_path,
        project_id=project_id,
        repo_url=repo_url,
        app_components=[component.model_dump() for component in app_components],
        infra_components=[component.model_dump() for component in infra_components],
        tools=tools,
        logger=logger,
    )

    if rename_map:
        for connection in connections:
            if connection.to_component in rename_map:
                connection.to_component = rename_map[connection.to_component]

    def _find_app_component(name: str):
        for component in app_components:
            if component.name == name:
                return component
        return app_components[0] if len(app_components) == 1 else None

    is_monorepo = len(app_components) > 1 or len({component.path for component in app_components}) > 1
    app_service_names = {
        component.name: f"app-{project_id}-{component.name}" if is_monorepo else f"app-{project_id}"
        for component in app_components
    }
    infra_service_names = {component.name: component.name for component in infra_components}

    for connection in connections:
        if connection.scope != "internal":
            continue
        target_component = _find_app_component(connection.from_component)
        if not target_component:
            raise ValueError(f"Missing application component for connection: {connection.from_component}")

        if connection.to_component in app_service_names:
            connection.to_component = app_service_names[connection.to_component]
        elif connection.to_component in infra_service_names:
            connection.to_component = infra_service_names[connection.to_component]

        env_var = None
        for existing in target_component.env_variables:
            if existing.key == connection.env_key:
                env_var = existing
                break

        if not env_var:
            raise ValueError(
                f"Missing env key '{connection.env_key}' for component '{target_component.name}'"
            )

        service_name = connection.to_component
        if connection.resolved_value:
            env_var.value = _replace_host_in_url(connection.resolved_value, service_name)
            env_var.source = "override"
        else:
            env_var.value = service_name
            env_var.source = "override"

    logger.info(f"[{project_id}] ✅ Planning complete.")
    ingress = None
    if app_components:
        rules = [
            IngressRule(
                path=component.ingress.path_prefix,
                service=component.name,
                port=component.port,
            )
            for component in app_components
            if component.ingress.expose
        ]
        rules.sort(key=lambda rule: (rule.path == "/", rule.path))
        ingress = IngressConfig(
            host=f"app-{project_id}.flowpilotai.me",
            tls=True,
            rules=rules,
        )

    return DeploymentPlan(
        is_monorepo=is_monorepo,
        components=[*app_components, *infra_components],
        connections=connections,
        ingress=ingress or IngressConfig(host=f"app-{project_id}.flowpilotai.me", tls=True, rules=[]),
    )
