"""Sub-agent: map connections between components and external services."""

from typing import List

from pydantic import BaseModel, Field

from agents.plan_schemas import Connection
from .agent_runner import run_agent


class ConnectionExtractionResult(BaseModel):
    """Structured output for connection extraction."""
    connections: List[Connection] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list, description="Validation errors that should block deployment")


SYSTEM_PROMPT = """You are a deployment planning sub-agent focused ONLY on connections.

Rules:
- Identify connections from environment variables and config files.
- Use scope=internal only when the target service is intended to run in-cluster.
- Use scope=external for third-party services and managed databases.
- Do NOT invent infrastructure components.
- Use resolved_value from config when available; for internal connections, use the in-cluster service name as the host.
- If a required env key is missing for a connection, add a descriptive entry to errors.
- Call ConnectionExtractionResult exactly once.
"""


def _format_app_summary(app_components: List[dict]) -> str:
    lines = []
    for app in app_components:
        envs = app.get("env_variables", []) or []
        env_keys = [env.get("key") for env in envs if env.get("key")]
        lines.append({
            "name": app.get("name"),
            "path": app.get("path"),
            "env_keys": env_keys,
        })
    return "\n".join(str(line) for line in lines)


def _format_infra_summary(infra_components: List[dict]) -> str:
    lines = []
    for infra in infra_components:
        credentials = list((infra.get("credentials") or {}).keys())
        envs = infra.get("env_variables", []) or []
        env_keys = [env.get("key") for env in envs if env.get("key")]
        lines.append({
            "name": infra.get("name"),
            "scope": infra.get("scope"),
            "owner_app": infra.get("owner_app"),
            "port": infra.get("port"),
            "credentials": credentials,
            "env_keys": env_keys,
        })
    return "\n".join(str(line) for line in lines)


def _user_prompt(
    project_id: str,
    repo_url: str,
    file_list_str: str,
    app_components: List[dict],
    infra_components: List[dict],
) -> str:
    return f"""Extract ONLY connections from this repository.

Project ID: {project_id}
Repository URL: {repo_url}

Application components (names, paths, env keys):
{_format_app_summary(app_components)}

Infrastructure components (names, scope, owners, credentials, env keys):
{_format_infra_summary(infra_components)}

Files in the repository:
{file_list_str}
"""


async def run_connection_mapper(
    *,
    file_list_str: str,
    local_path: str,
    project_id: str,
    repo_url: str,
    app_components: List[dict],
    infra_components: List[dict],
    tools,
    logger,
) -> List[Connection]:
    agent_state = {
        "local_path": local_path,
        "project_id": project_id,
    }

    result = await run_agent(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=_user_prompt(project_id, repo_url, file_list_str, app_components, infra_components),
        output_tool=ConnectionExtractionResult,
        tools=tools,
        agent_state=agent_state,
        logger=logger,
    )

    if result.errors:
        raise ValueError("; ".join(result.errors))

    return result.connections
