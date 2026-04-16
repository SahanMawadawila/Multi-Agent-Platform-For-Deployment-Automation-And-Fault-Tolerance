"""Sub-agent: extract application components."""

from typing import List

from pydantic import BaseModel, Field

from agents.plan_schemas import ApplicationComponent
from .agent_runner import run_agent


class ComponentExtractionResult(BaseModel):
    """Structured output for application component extraction."""
    components: List[ApplicationComponent] = Field(default_factory=list)


SYSTEM_PROMPT = """You are a deployment planning sub-agent focused ONLY on application components.

Your output must include ONLY buildable application services. Do NOT include databases, caches,
message brokers, or any other infrastructure components.

Rules:
- Find each deployable app component and fill all ApplicationComponent fields.
- Read actual source/config files to find health check paths (do not guess).
- Use package.json/pom.xml/pyproject for build/run commands and versions.
- Populate env_variables from .env/.env.example/config files.
- Set ingress.expose true only for user-facing services.
- Call ComponentExtractionResult exactly once.
"""


def _user_prompt(project_id: str, repo_url: str, file_list_str: str) -> str:
    return f"""Extract ONLY application components from this repository.

Project ID: {project_id}
Repository URL: {repo_url}

Files in the repository:
{file_list_str}
"""


async def run_component_extractor(
    *,
    file_list_str: str,
    local_path: str,
    project_id: str,
    repo_url: str,
    tools,
    logger,
) -> List[ApplicationComponent]:
    agent_state = {
        "local_path": local_path,
        "project_id": project_id,
    }

    result = await run_agent(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=_user_prompt(project_id, repo_url, file_list_str),
        output_tool=ComponentExtractionResult,
        tools=tools,
        agent_state=agent_state,
        logger=logger,
    )

    return result.components
