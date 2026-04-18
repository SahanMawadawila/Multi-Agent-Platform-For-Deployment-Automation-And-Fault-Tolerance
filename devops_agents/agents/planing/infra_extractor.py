"""Sub-agent: extract infrastructure components from explicit repo sources."""

from typing import List

from pydantic import BaseModel, Field

from agents.plan_schemas import InfrastructureComponent
from .agent_runner import run_agent


class InfraExtractionResult(BaseModel):
    """Structured output for infrastructure component extraction."""
    components: List[InfrastructureComponent] = Field(default_factory=list)


SYSTEM_PROMPT = """You are a deployment planning sub-agent focused ONLY on infrastructure components.

You may extract infrastructure from explicit repo definitions (docker-compose, Helm, K8s manifests,
or other YAML deployment configs), and you may also infer missing infra from application configuration
and environment variables. If infra is inferred, choose reasonable defaults and mark credentials from
config when available.

Rules:
- Use the exact Docker image and tag from repo files when explicit.
- If infra is inferred, use a common official image and a stable tag.
- Set storage to null unless there is an explicit volume/claim definition.
- Set scope to "project" or "global".
- If scope is "project", set owner_app.
- If scope is "project", name must be "<appname>-<infraname>".
- If any infra-only YAML/compose/Helm snippet exists, attach it as manifest_yaml for that component.
- Call InfraExtractionResult exactly once.
"""


def _format_app_summary(app_components: List[dict]) -> str:
    lines = []
    for app in app_components:
        lines.append({
            "name": app.get("name"),
            "path": app.get("path"),
        })
    return "\n".join(str(line) for line in lines)


def _user_prompt(project_id: str, repo_url: str, file_list_str: str, app_components: List[dict]) -> str:
    return f"""Extract infrastructure components for this repository.

Project ID: {project_id}
Repository URL: {repo_url}

Application components (names, paths):
{_format_app_summary(app_components)}

Files in the repository:
{file_list_str}
"""


async def run_infra_extractor(
    *,
    file_list_str: str,
    local_path: str,
    project_id: str,
    repo_url: str,
    app_components: List[dict],
    tools,
    logger,
) -> List[InfrastructureComponent]:
    agent_state = {
        "local_path": local_path,
        "project_id": project_id,
    }

    result = await run_agent(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=_user_prompt(project_id, repo_url, file_list_str, app_components),
        output_tool=InfraExtractionResult,
        tools=tools,
        agent_state=agent_state,
        logger=logger,
    )

    return result.components
