"""Sub-agent: extract infrastructure components from explicit repo sources."""

import json
import os
import logging
from typing import List

from pydantic import BaseModel, Field

from agents.plan_schemas import InfrastructureComponent
from .agent_runner import run_agent

logger = logging.getLogger("infra_extractor")


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
- Do NOT extract an infrastructure component if an application component already serves the same purpose or provides the same service. Review the provided application components carefully to prevent duplication.
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


# ---------------------------------------------------------------------------
# Registry post-processing
# ---------------------------------------------------------------------------

_registry_cache = None


def _load_registry() -> dict:
    """Load the infra registry JSON."""
    global _registry_cache
    if _registry_cache is not None:
        return _registry_cache

    # __file__ is at agents/planing/infra_extractor.py
    # Go up 3 levels: planing -> agents -> devops_agents (project root)
    agents_dir = os.path.dirname(os.path.abspath(__file__))       # agents/planing/
    agents_parent = os.path.dirname(agents_dir)                    # agents/
    project_root = os.path.dirname(agents_parent)                  # devops_agents/
    config_path = os.path.join(project_root, "config", "infra_registry.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            _registry_cache = json.load(f)
    except Exception:
        _registry_cache = {}
    return _registry_cache


def _match_registry_key(component: InfrastructureComponent) -> str | None:
    """Match a component to a registry key by name or image."""
    registry = _load_registry()

    comp_name = (component.name or "").lower()
    comp_image = (component.image or "").lower()

    aliases = {
        "postgresql": ["postgres", "postgresql", "pg"],
        "mongodb": ["mongo", "mongodb"],
        "mysql": ["mysql", "mariadb"],
        "redis": ["redis"],
        "rabbitmq": ["rabbitmq", "rabbit"],
        "kafka": ["kafka"],
    }

    for reg_key, keywords in aliases.items():
        for kw in keywords:
            if kw in comp_name or kw in comp_image:
                if reg_key in registry:
                    return reg_key

    return None


def _post_process_with_registry(
    components: List[InfrastructureComponent],
) -> List[InfrastructureComponent]:
    """
    Post-process LLM-extracted infra components against the template registry.

    For each component:
      - Set template_key if it matches a registry entry
      - Override image to a tested version if the LLM picked something untested
      - Populate supported_versions so frontend can offer a dropdown
      - Set default credentials from registry if LLM missed them
    """
    registry = _load_registry()

    for comp in components:
        reg_key = _match_registry_key(comp)
        if not reg_key:
            # Not in registry — will use LLM fallback at deployment time
            logger.info(f"Infra component '{comp.name}' not in registry — will use LLM fallback")
            continue

        entry = registry[reg_key]
        comp.template_key = reg_key
        comp.supported_versions = entry.get("supported_versions", [])

        # Validate image — if LLM picked an untested version, use registry default
        supported = entry.get("supported_versions", [])
        if supported:
            # Extract the tag from the image (e.g., "postgres:16-alpine" -> "16-alpine")
            image_tag = comp.image.split(":")[-1] if ":" in comp.image else ""
            if image_tag not in supported:
                default_image = entry.get("default_image", comp.image)
                logger.info(
                    f"Image tag '{image_tag}' for {comp.name} not in tested versions {supported}. "
                    f"Overriding to '{default_image}'"
                )
                comp.image = default_image

        # Ensure port matches registry default if LLM got it wrong
        default_port = entry.get("default_port")
        if default_port and comp.port != default_port:
            logger.info(f"Overriding port for {comp.name}: {comp.port} -> {default_port}")
            comp.port = default_port

        # Fill in missing credentials from registry defaults
        default_creds = entry.get("default_credentials", {})
        existing_cred_keys = set(comp.credentials.keys()) if comp.credentials else set()
        for cred_key, cred_spec in default_creds.items():
            if cred_key not in existing_cred_keys:
                from agents.plan_schemas import CredentialField
                comp.credentials[cred_key] = CredentialField(
                    value="",
                    source="auto_generate" if cred_spec.get("default") == "auto_generate" else "detected",
                    editable=True,
                    sensitive=True,
                )

    return components


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

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

    # Post-process against the template registry
    components = _post_process_with_registry(result.components)

    return components
