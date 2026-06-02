"""
Deployment Error Classifier

Uses Pydantic structured output to classify each failing component's error
into one of: application_error, image_creation_error, gitops_fix, ingress_issue.
"""

import json
import logging
from typing import List, Literal
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from config.settings import settings
from app.kafka_terminal_producer import send_terminal_message

logger = logging.getLogger("error_classifier")


# ============== PYDANTIC SCHEMAS ==============

class ComponentError(BaseModel):
    """Classification result for a single failing component."""
    component_name: str = Field(..., description="Name of the failing component (e.g., 'frontend', 'account-service')")
    error_type: Literal["application_error", "image_creation_error", "gitops_fix", "ingress_issue"] = Field(
        ...,
        description=(
            "The category of error: "
            "'application_error' = code/config bug in the application source (e.g., missing files, bad nginx.conf, missing dependency); "
            "'image_creation_error' = the container image failed to build in CI/CD (buildpack/Docker errors); "
            "'gitops_fix' = Kubernetes manifest issue (wrong env vars, bad probes, wrong image tag, resource limits, missing secrets); "
            "'ingress_issue' = Ingress routing misconfiguration (wrong paths, wrong ports, TLS issues)"
        )
    )
    error_summary: str = Field(..., description="A concise summary of the root cause of this component's failure")


class DeploymentErrorClassification(BaseModel):
    """Structured classification of all deployment errors."""
    component_errors: List[ComponentError] = Field(
        ..., description="List of classified errors, one per failing component"
    )
    fix_order_summary: str = Field(
        ..., description="Brief explanation of why you classified each error the way you did"
    )


# ============== CLASSIFIER PROMPT ==============

CLASSIFIER_PROMPT = """You are an expert Kubernetes deployment error analyst. 
You will receive error logs from a failed Kubernetes deployment. Multiple pods/components may be failing.

Your job is to classify EACH failing component's error into exactly one of these categories:

1. **application_error**: The application source code or configuration has a bug.
   Examples: missing files/directories (e.g., nginx logs directory), bad application config files (nginx.conf, application.yml), 
   missing dependencies in package.json/pom.xml, application code throwing unhandled exceptions, 
   missing Spring Boot actuator dependency causing health check 404s.

2. **image_creation_error**: The container image failed to build in CI/CD (GitHub Actions).
   Examples: buildpack compilation errors, dependency download failures, build script errors.
   NOTE: If the pod is running but crashing, it is NOT an image creation error — the image was built successfully.

3. **gitops_fix**: The Kubernetes manifest YAML has an issue that can be fixed in the GitOps repo.
   Examples: wrong environment variable values, incorrect probe configuration (wrong path, too aggressive timeouts), 
   wrong image tag, missing ConfigMap/Secret references, resource limits too low (OOMKilled), 
   wrong container port, missing volume mounts.

4. **ingress_issue**: The Ingress resource is misconfigured.
   Examples: wrong path routing, wrong backend service name or port, missing TLS configuration, 
   wrong hostname, 502/503 errors from the load balancer.

IMPORTANT RULES:
- If a pod is in CrashLoopBackOff and the logs show an APPLICATION error (like missing files, bad config), classify as application_error.
- If a pod is in CrashLoopBackOff and the logs show a PROBE failure (404 on /actuator/health, wrong port), classify as gitops_fix.
- If multiple components are failing because a dependency (like RabbitMQ) is down, classify the ROOT CAUSE component, not the dependent services.
- Be precise: one classification per DISTINCT failing component.
- Do NOT classify healthy/running pods.
"""


# ============== CLASSIFIER FUNCTION ==============

async def classify_deployment_errors(
    error_logs: str,
    project_id: str,
) -> DeploymentErrorClassification:
    """
    Classify deployment errors per component using LLM structured output.
    
    Args:
        error_logs: Aggregated error logs from deployment_monitor_agent
        project_id: Project identifier for terminal messages
        
    Returns:
        DeploymentErrorClassification with per-component error types
    """
    send_terminal_message(project_id, "🔍 Classifying deployment errors per component...\n\r")
    
    llm = ChatOpenAI(
        model="gpt-4.1-mini",
        api_key=settings.openai_key,
        temperature=0,
    )
    
    llm_structured = llm.with_structured_output(DeploymentErrorClassification)
    
    messages = [
        SystemMessage(content=CLASSIFIER_PROMPT),
        HumanMessage(content=f"Here are the deployment error logs:\n\n{error_logs}"),
    ]
    
    try:
        classification = await llm_structured.ainvoke(messages)
        
        # Log the classification
        app_errors = [e for e in classification.component_errors if e.error_type == "application_error"]
        image_errors = [e for e in classification.component_errors if e.error_type == "image_creation_error"]
        gitops_errors = [e for e in classification.component_errors if e.error_type == "gitops_fix"]
        ingress_errors = [e for e in classification.component_errors if e.error_type == "ingress_issue"]
        
        summary_parts = []
        if app_errors:
            summary_parts.append(f"{len(app_errors)} application error(s)")
        if image_errors:
            summary_parts.append(f"{len(image_errors)} image build error(s)")
        if gitops_errors:
            summary_parts.append(f"{len(gitops_errors)} GitOps manifest error(s)")
        if ingress_errors:
            summary_parts.append(f"{len(ingress_errors)} ingress issue(s)")
        
        send_terminal_message(
            project_id,
            f"📋 Error Classification: {', '.join(summary_parts) if summary_parts else 'No errors classified'}\n\r"
        )
        
        for ce in classification.component_errors:
            emoji = {
                "application_error": "🐛",
                "image_creation_error": "🏗️",
                "gitops_fix": "📝",
                "ingress_issue": "🌐",
            }.get(ce.error_type, "❓")
            send_terminal_message(
                project_id,
                f"   {emoji} {ce.component_name}: {ce.error_type} — {ce.error_summary}\n\r"
            )
        
        logger.info(f"[{project_id}] Classified {len(classification.component_errors)} errors: {classification.fix_order_summary}")
        return classification
        
    except Exception as e:
        logger.error(f"[{project_id}] Error classification failed: {e}")
        send_terminal_message(project_id, f"⚠️ Error classification failed: {e}. Falling back to generic fix.\n\r")
        
        # Fallback: treat everything as a gitops_fix (the old behavior)
        return DeploymentErrorClassification(
            component_errors=[
                ComponentError(
                    component_name="unknown",
                    error_type="gitops_fix",
                    error_summary=f"Classification failed: {str(e)}. Treating as GitOps issue.",
                )
            ],
            fix_order_summary="Fallback classification due to error",
        )
