"""Sub-agent: extract infrastructure components from explicit repo sources."""

from typing import List

from pydantic import BaseModel, Field

from agents.plan_schemas import InfrastructureComponent
from .agent_runner import run_agent


class InfraExtractionResult(BaseModel):
    """Structured output for infrastructure component extraction."""
    components: List[InfrastructureComponent] = Field(default_factory=list)


SYSTEM_PROMPT = """You are a deployment planning sub-agent focused ONLY on infrastructure components.

Only include infrastructure services that are explicitly declared in the repository
(e.g., docker-compose files, Helm charts, Kubernetes manifests, or documented images in README).
Do NOT infer or invent infrastructure from application config alone.

Rules:
- Use the exact Docker image and tag from repo files.
- If no explicit infra definition exists, return an empty list.
- Set storage to null unless there is an explicit volume/claim definition.
- Include depends_on only when declared in compose/manifest files.
- Call InfraExtractionResult exactly once.
"""


def _user_prompt(project_id: str, repo_url: str, file_list_str: str) -> str:
    return f"""Extract ONLY infrastructure components explicitly defined in this repository.

Project ID: {project_id}
Repository URL: {repo_url}

Files in the repository:
{file_list_str}
"""


async def run_infra_extractor(
    *,
    file_list_str: str,
    local_path: str,
    project_id: str,
    repo_url: str,
    tools,
    logger,
) -> List[InfrastructureComponent]:
    agent_state = {
        "local_path": local_path,
        "project_id": project_id,
    }

    result = await run_agent(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=_user_prompt(project_id, repo_url, file_list_str),
        output_tool=InfraExtractionResult,
        tools=tools,
        agent_state=agent_state,
        logger=logger,
    )

    return result.components
