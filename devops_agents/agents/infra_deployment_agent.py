"""
Infrastructure Deployment Agent — Template Registry Edition

Generates K8s manifests for infrastructure components using pre-tested
Jinja2 templates from the infra registry. Falls back to LLM generation
for unsupported (custom) components.

Outputs into temp/gitops_{project_id}/app/infra/{service_name}/
"""

import json
import os
import secrets
import string
import logging

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from app.kafka_terminal_producer import send_terminal_message
from config.settings import settings

logger = logging.getLogger("infra_deployment_agent")

# ---------------------------------------------------------------------------
# Registry loader
# ---------------------------------------------------------------------------

_registry_cache = None


def _load_registry() -> dict:
    """Load the infra registry JSON (cached after first call)."""
    global _registry_cache
    if _registry_cache is not None:
        return _registry_cache

    config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "config", "infra_registry.json"
    )
    with open(config_path, "r", encoding="utf-8") as f:
        _registry_cache = json.load(f)
    return _registry_cache


def _lookup_registry(component: dict) -> tuple[str | None, dict | None]:
    """
    Match a plan's infra component to a registry entry.

    Matching priority:
      1. Explicit template_key from the plan (set by infra_extractor post-processing)
      2. Component name contains a registry key (e.g., 'backend-postgres' matches 'postgresql')
      3. Image name contains a registry key (e.g., 'mongo:7.0' matches 'mongodb')

    Returns (registry_key, registry_entry) or (None, None).
    """
    registry = _load_registry()

    # 1. Explicit key
    template_key = component.get("template_key")
    if template_key and template_key in registry:
        return template_key, registry[template_key]

    comp_name = (component.get("name") or "").lower()
    comp_image = (component.get("image") or "").lower()

    # Alias map for fuzzy matching
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
                    return reg_key, registry[reg_key]

    return None, None


# ---------------------------------------------------------------------------
# Credential resolver
# ---------------------------------------------------------------------------

def _generate_password(length: int = 16) -> str:
    """Generate a random alphanumeric password."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _resolve_credentials(
    registry_entry: dict,
    component: dict,
    project_id: str,
) -> dict:
    """
    Merge registry defaults with user-supplied credential values from the plan.

    For each credential in the registry:
      - If the user provided a value in the plan → use it
      - If the default is 'auto_generate' → generate a random password
      - Otherwise → use the default, with {project_id} placeholder replaced
    """
    default_creds = registry_entry.get("default_credentials", {})
    plan_creds = component.get("credentials") or {}
    resolved = {}

    for cred_key, cred_spec in default_creds.items():
        env_key = cred_spec["env_key"]
        default_val = cred_spec["default"]

        # Check if user overrode this credential in the plan
        user_val = None
        if cred_key in plan_creds:
            user_entry = plan_creds[cred_key]
            if isinstance(user_entry, dict):
                user_val = user_entry.get("value")
            elif isinstance(user_entry, str):
                user_val = user_entry

        if user_val:
            resolved[cred_key] = {"env_key": env_key, "value": user_val}
        elif default_val == "auto_generate":
            resolved[cred_key] = {"env_key": env_key, "value": _generate_password()}
        else:
            val = default_val.replace("{project_id}", project_id)
            resolved[cred_key] = {"env_key": env_key, "value": val}

    return resolved


# ---------------------------------------------------------------------------
# Template renderer
# ---------------------------------------------------------------------------

def _render_template(
    registry_key: str,
    registry_entry: dict,
    component: dict,
    project_id: str,
) -> str:
    """Render a Jinja2 infra template with resolved values."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    templates_dir = os.path.join(base_dir, "templates", "k8s", "infra")
    env = Environment(loader=FileSystemLoader(templates_dir))

    template_name = registry_entry.get("template_name", registry_key)
    template = env.get_template(f"{template_name}.j2")

    # Resolve credentials
    credentials = _resolve_credentials(registry_entry, component, project_id)

    # Resolve resources
    default_res = registry_entry.get("default_resources", {})
    plan_res = component.get("resources") or {}

    # Resolve storage
    default_storage = registry_entry.get("default_storage") or {}
    plan_storage = component.get("storage") or {}
    storage_size = plan_storage.get("size") or default_storage.get("size", "1Gi")
    storage_class = plan_storage.get("storage_class") or default_storage.get("storage_class", "gp2")

    # Resolve image — user may have picked a different version
    image = component.get("image") or registry_entry.get("default_image", "")

    # Env variables from the plan (extra user-specified vars)
    env_variables = component.get("env_variables") or []

    # Build template context
    context = {
        "service_name": component.get("name", registry_key),
        "namespace": project_id,
        "image": image,
        "port": component.get("port") or registry_entry.get("default_port", 5432),
        "credentials": credentials,
        "env_variables": env_variables,
        "storage_size": storage_size,
        "storage_class": storage_class,
        "cpu_request": plan_res.get("cpu_request") or default_res.get("cpu_request", "200m"),
        "memory_request": plan_res.get("memory_request") or default_res.get("memory_request", "256Mi"),
        "cpu_limit": plan_res.get("cpu_limit") or default_res.get("cpu_limit", "500m"),
        "memory_limit": plan_res.get("memory_limit") or default_res.get("memory_limit", "512Mi"),
    }

    # Kafka-specific fields
    if registry_key == "kafka":
        context["zookeeper_image"] = registry_entry.get("zookeeper_image", "confluentinc/cp-zookeeper:7.6.0")
        context["internal_port"] = registry_entry.get("internal_port", 29092)
        context["zookeeper_port"] = registry_entry.get("zookeeper_port", 2181)

    # RabbitMQ management port
    if registry_key == "rabbitmq":
        context["management_port"] = registry_entry.get("management_port", 15672)

    return template.render(context)


# ---------------------------------------------------------------------------
# LLM fallback (for unsupported/custom components)
# ---------------------------------------------------------------------------

async def _llm_fallback_generator(
    component: dict,
    project_id: str,
    manifests_path: str,
) -> None:
    """
    Fallback: use LLM to generate manifests for components not in the registry.
    This is the old infra_deployment_agent logic, kept as a safety net.
    """
    service_name = component.get("name")
    send_terminal_message(
        project_id,
        f"⚠️ {service_name} is not in the template registry. Using AI fallback...\\n\\r",
    )

    llm = ChatOpenAI(
        model="gpt-4.1-mini",
        api_key=settings.openai_key,
        temperature=0,
    )

    system_prompt = (
        "You are a Kubernetes expert. Generate only valid Kubernetes YAML. "
        "Output MUST be plain YAML, no markdown or explanations. "
        "Create infrastructure manifests that are fully deployable on Kubernetes. "
        "Namespace MUST be exactly the provided namespace value. "
        "CRITICAL RULES: "
        "1. NEVER use emptyDir for data volumes. Use PersistentVolumeClaim with storageClassName: gp2. "
        "2. Only generate the actual StatefulSet/Deployment, Service, PVC, and Secret. "
        "3. For liveness and readiness probes, add initialDelaySeconds of at least 90. "
        "4. Add a startupProbe with failureThreshold of 30 and periodSeconds of 5."
    )

    user_payload = {
        "project_id": project_id,
        "namespace": project_id,
        "infra_component": component,
    }

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=json.dumps(user_payload, indent=2)),
    ]

    response = await llm.ainvoke(messages)
    manifest_yaml = response.content.strip()

    if manifest_yaml.startswith("```"):
        lines = manifest_yaml.split("\n")
        manifest_yaml = "\n".join(
            lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        )

    output_path = os.path.join(manifests_path, "infra-manifest.yaml")
    with open(output_path, "w") as f:
        f.write(manifest_yaml)


# ---------------------------------------------------------------------------
# Main agent entry point
# ---------------------------------------------------------------------------

async def infra_deployment_agent(state: dict):
    """
    Generates K8s manifests for infrastructure components.

    Uses pre-tested Jinja2 templates for known components (PostgreSQL, MongoDB,
    MySQL, Redis, RabbitMQ, Kafka). Falls back to LLM generation for anything
    not in the registry.

    Outputs into temp/gitops_{project_id}/app/infra/{service_name}/
    """
    project_id = state.get("project_id", "")
    component = state.get("infra_component") or {}
    service_name = component.get("name")

    send_terminal_message(
        project_id,
        f"🧱 Generating infra manifests for {service_name or 'infra'}...\\n\\r",
    )

    gitops_base = state.get("gitops_dir")
    manifests_path = os.path.join(gitops_base, "app", "infra", service_name or "infra")
    os.makedirs(manifests_path, exist_ok=True)

    # Try registry lookup
    registry_key, registry_entry = _lookup_registry(component)

    if registry_entry:
        # ✅ Template path — deterministic, no LLM
        send_terminal_message(
            project_id,
            f"📦 Using tested template: {registry_entry['display_name']}\\n\\r",
        )
        logger.info(
            f"[{project_id}] Rendering template '{registry_key}' for {service_name}"
        )

        try:
            manifest_yaml = _render_template(
                registry_key, registry_entry, component, project_id
            )

            output_path = os.path.join(manifests_path, "infra-manifest.yaml")
            with open(output_path, "w") as f:
                f.write(manifest_yaml)

            send_terminal_message(
                project_id,
                f"📄 Generated infra/{service_name}/infra-manifest.yaml (template: {registry_key})\\n\\r",
            )
        except Exception as e:
            logger.error(
                f"[{project_id}] Template render failed for {registry_key}: {e}"
            )
            send_terminal_message(
                project_id,
                f"⚠️ Template render failed for {service_name}: {e}. Falling back to AI...\\n\\r",
            )
            await _llm_fallback_generator(component, project_id, manifests_path)
    else:
        # ❌ Not in registry — LLM fallback
        logger.info(
            f"[{project_id}] No registry entry for {service_name}, using LLM fallback"
        )
        await _llm_fallback_generator(component, project_id, manifests_path)

    send_terminal_message(
        project_id,
        f"✅ Infra manifests ready for {service_name or 'infra'}.\\n\\r",
    )

    return {"infra_status": "manifests_ready"}
