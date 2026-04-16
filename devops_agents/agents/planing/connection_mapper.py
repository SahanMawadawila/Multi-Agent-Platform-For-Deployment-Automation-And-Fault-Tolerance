"""Sub-agent: map connections between components and external services."""

from typing import List

from pydantic import BaseModel, Field

from agents.plan_schemas import Connection
from .agent_runner import run_agent


class ConnectionExtractionResult(BaseModel):
    """Structured output for connection extraction."""
    connections: List[Connection] = Field(default_factory=list)


SYSTEM_PROMPT = """You are a deployment planning sub-agent focused ONLY on connections.

Rules:
- Identify connections from environment variables and config files.
- Use scope=internal only when the target service is intended to run in-cluster.
- Use scope=external for third-party services and managed databases.
- Do NOT invent infrastructure components.
- Use resolved_value from config when available; prefer in-cluster service names for internal.
- Call ConnectionExtractionResult exactly once.
"""


def _user_prompt(project_id: str, repo_url: str, file_list_str: str) -> str:
    return f"""Extract ONLY connections from this repository.

Project ID: {project_id}
Repository URL: {repo_url}

Files in the repository:
{file_list_str}
"""


async def run_connection_mapper(
    *,
    file_list_str: str,
    local_path: str,
    project_id: str,
    repo_url: str,
    tools,
    logger,
) -> List[Connection]:
    agent_state = {
        "local_path": local_path,
        "project_id": project_id,
    }

    result = await run_agent(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=_user_prompt(project_id, repo_url, file_list_str),
        output_tool=ConnectionExtractionResult,
        tools=tools,
        agent_state=agent_state,
        logger=logger,
    )

    return result.connections
