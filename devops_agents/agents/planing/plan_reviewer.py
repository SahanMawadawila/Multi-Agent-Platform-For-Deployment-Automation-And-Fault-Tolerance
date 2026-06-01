"""Sub-agent: review the draft deployment plan, extract connections, and fix env variables."""

import json
from typing import List

from pydantic import BaseModel, Field

from agents.plan_schemas import Connection, EnvCorrection
from .agent_runner import run_agent


class PlanReviewResult(BaseModel):
    """Structured output for the plan reviewer."""
    connections: List[Connection] = Field(default_factory=list)
    env_corrections: List[EnvCorrection] = Field(default_factory=list)


SYSTEM_PROMPT = """You are the FINAL REVIEWER of a Kubernetes deployment plan.

You receive a draft plan containing application components and infrastructure components (as JSON).
You have access to read source files from the repository for verification.

Your TWO jobs:

━━━ JOB 1: Extract Connections ━━━
Identify every connection between components:
- app → infra (e.g., backend connects to postgres)
- app → app (e.g., frontend calls backend API)
- app → external (e.g., app calls Stripe API)

For each connection provide `env_updates` — the env variables the source component needs for this
connection to work IN KUBERNETES. The values must be Kubernetes-ready:
- Replace localhost / 127.0.0.1 / 0.0.0.0 / docker-compose service names with the K8s service name
  (which is the target component's `name` field from the plan).
- Use the exact `port` from the target component in the plan.
- Use actual credential values from the infra component's `credentials` dict or from source code.
- For JDBC/MongoDB/Redis connection strings, rewrite the full URL with the correct K8s host and port.

━━━ JOB 2: Fix Env Variable Issues ━━━
Scan ALL env variables across ALL components. For each problem, add an EnvCorrection:
- Any value containing "localhost", "127.0.0.1", or "0.0.0.0" must be rewritten to the K8s service name.
- Any value containing "TODO" or placeholder text must be replaced with the actual value from source code
  or from the infra component's credentials.
- Any port in a connection URL that doesn't match the target component's port must be corrected.
- Any credential that exists in an infra component's `credentials` but is missing or wrong in the
  connected app's env vars must be corrected.

━━━ CHAIN OF THOUGHT ━━━
Before producing output, reason step-by-step through these checks:
1. For EVERY component (both app and infra), list its env variables that reference other services or contain localhost.
2. For each such variable, identify which component it connects to.
3. Verify: Does the URL/host use the K8s service name (component name)? Is the port correct?
4. Verify: Are credentials from infra components propagated correctly?
5. If everything is correct, produce the output. If not, add corrections.

━━━ RULES ━━━
- NEVER invent infrastructure components.
- Use scope=internal for in-cluster connections, scope=external for third-party services.
- Call PlanReviewResult exactly once with your final answer.
"""


def _format_plan_json(app_components: List[dict], infra_components: List[dict]) -> str:
    """Format the draft plan as readable JSON for the reviewer."""
    plan = {
        "application_components": app_components,
        "infrastructure_components": infra_components,
    }
    return json.dumps(plan, indent=2, default=str)


def _user_prompt(
    project_id: str,
    repo_url: str,
    file_list_str: str,
    app_components: List[dict],
    infra_components: List[dict],
) -> str:
    plan_json = _format_plan_json(app_components, infra_components)
    return f"""Review this deployment plan and extract connections + fix any env variable issues.

Project ID: {project_id}
Repository URL: {repo_url}

━━━ DRAFT PLAN (JSON) ━━━
{plan_json}

━━━ FILES IN REPOSITORY ━━━
{file_list_str}
"""


async def run_plan_reviewer(
    *,
    file_list_str: str,
    local_path: str,
    project_id: str,
    repo_url: str,
    app_components: List[dict],
    infra_components: List[dict],
    tools,
    logger,
) -> PlanReviewResult:
    agent_state = {
        "local_path": local_path,
        "project_id": project_id,
    }

    result = await run_agent(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=_user_prompt(project_id, repo_url, file_list_str, app_components, infra_components),
        output_tool=PlanReviewResult,
        tools=tools,
        agent_state=agent_state,
        logger=logger,
    )

    return result
