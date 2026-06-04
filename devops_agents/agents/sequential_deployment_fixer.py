"""
Sequential Deployment Fixer

Orchestrates error fixing in dependency order:
  1. Application errors  → fix source code, push, wait for image rebuild
  2. Image creation errors → use error_fixing_agent to fix CI/CD
  3. GitOps errors → fix K8s manifests in the GitOps repo
  4. Ingress issues → fix ingress configuration in the GitOps repo

This is a single node in the post-processing graph that internally
orchestrates sub-agents sequentially.
"""

import os
import asyncio
import subprocess
import json
import logging
from typing import Dict, List, Optional

from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode

from agents.error_classifier import classify_deployment_errors, ComponentError
from agents.app_error_fixer_agent import run_app_error_fixer
from agents.deployment_fixer_agent import (
    deployment_fixer_agent,
    deployment_fixer_tool_node,
    tools as gitops_tools,
    DEPLOYMENT_FIXER_PROMPT,
    DeploymentFixComplete,
)
from agents.monitor_agent import build_monitor_agent, fetch_build_logs
from tools.git_tools import AsyncGitTools
from config.settings import settings
from app.kafka_terminal_producer import send_terminal_message

logger = logging.getLogger("sequential_deployment_fixer")


async def _wait_for_image_rebuild(
    project_id: str,
    component_name: str,
    repo_owner: str,
    repo_name: str,
    local_path: str,
) -> bool:
    """
    Wait for a GitHub Actions image rebuild to complete.
    Re-uses the build_monitor_agent logic.
    
    Returns True if the build succeeded, False otherwise.
    """
    send_terminal_message(
        project_id,
        f"⏳ Waiting for image rebuild of {component_name}...\n\r",
    )
    
    component = {"name": component_name}
    monitor_state = {
        "repo_owner": repo_owner,
        "repo_name": repo_name,
        "project_id": project_id,
        "build_id": "",
        "local_path": local_path,
        "component": component,
    }
    
    result = await build_monitor_agent(monitor_state)
    build_status = result.get("build_status", "")
    
    if build_status == "success":
        send_terminal_message(project_id, f"✅ Image rebuild succeeded for {component_name}\n\r")
        return True
    else:
        send_terminal_message(
            project_id,
            f"❌ Image rebuild failed for {component_name}: {result.get('build_error_logs', 'unknown error')[:200]}\n\r",
        )
        return False


async def _fix_gitops_errors(
    project_id: str,
    component_errors: List[ComponentError],
    gitops_dir: str,
) -> bool:
    """
    Fix GitOps manifest errors using an LLM with gitops repo tools.
    Operates on the {gitops_dir}_push directory.
    
    Returns True if fixes were applied and pushed.
    """
    if not component_errors:
        return True
    
    error_descriptions = "\n".join(
        f"- {ce.component_name}: {ce.error_summary}"
        for ce in component_errors
    )
    
    send_terminal_message(project_id, f"📝 Fixing GitOps manifest errors for {len(component_errors)} component(s)...\n\r")
    
    push_dir = f"{gitops_dir}_push"
    
    llm = ChatOpenAI(model="o4-mini", api_key=settings.openai_key)
    llm_with_tools = llm.bind_tools(gitops_tools)
    
    tool_state = {
        "gitops_dir": gitops_dir,
        "project_id": project_id,
    }
    
    messages = [
        SystemMessage(content=DEPLOYMENT_FIXER_PROMPT),
        HumanMessage(content=(
            f"The following components have GitOps manifest issues:\n\n"
            f"{error_descriptions}\n\n"
            f"Please investigate the GitOps repo and fix the manifests."
        )),
    ]
    
    for iteration in range(20):
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)
        
        if not hasattr(response, "tool_calls") or not response.tool_calls:
            break
        
        for tc in response.tool_calls:
            if tc["name"] == "DeploymentFixComplete":
                is_app_issue = tc["args"].get("is_app_issue", False)
                fix_applied = tc["args"].get("fix_applied", "No fix")
                error = tc["args"].get("error", "Unknown")
                
                if not is_app_issue:
                    send_terminal_message(
                        project_id,
                        f"✅ GitOps fix applied: {fix_applied}\n\r",
                    )
                    return True
                else:
                    send_terminal_message(
                        project_id,
                        f"⚠️ GitOps fixer determined this is an app issue: {error}\n\r",
                    )
                    return False
            
            # Execute tool
            tool_node_state = {**tool_state, "messages": [response]}
            node = ToolNode(gitops_tools)
            try:
                result = await node.ainvoke(tool_node_state)
                for msg in result.get("messages", []):
                    messages.append(msg)
            except Exception as e:
                logger.error(f"[{project_id}] GitOps tool error: {e}")
                messages.append(ToolMessage(
                    tool_call_id=tc["id"],
                    content=f"Error: {str(e)}",
                ))
    
    return False


async def _fix_ingress_errors(
    project_id: str,
    component_errors: List[ComponentError],
    gitops_dir: str,
) -> bool:
    """
    Fix ingress configuration errors.
    Uses the same GitOps tools but with an ingress-specific prompt.
    """
    if not component_errors:
        return True
    
    error_descriptions = "\n".join(
        f"- {ce.component_name}: {ce.error_summary}"
        for ce in component_errors
    )
    
    send_terminal_message(project_id, f"🌐 Fixing ingress issues...\n\r")
    
    llm = ChatOpenAI(model="o4-mini", api_key=settings.openai_key)
    llm_with_tools = llm.bind_tools(gitops_tools)
    
    tool_state = {
        "gitops_dir": gitops_dir,
        "project_id": project_id,
    }
    
    ingress_prompt = (
        "You are an expert Kubernetes Ingress engineer. An ingress configuration issue has been detected.\n"
        "Use the GitOps repository tools to inspect and fix the ingress.yaml manifest.\n"
        "Common fixes: wrong path routing, wrong backend service name/port, missing annotations.\n"
        "After fixing, use commit_and_push to apply changes. Then call DeploymentFixComplete.\n"
    )
    
    messages = [
        SystemMessage(content=ingress_prompt),
        HumanMessage(content=(
            f"The following ingress issues were detected:\n\n"
            f"{error_descriptions}\n\n"
            f"Please fix the ingress configuration in the GitOps repo."
        )),
    ]
    
    for iteration in range(15):
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)
        
        if not hasattr(response, "tool_calls") or not response.tool_calls:
            break
        
        for tc in response.tool_calls:
            if tc["name"] == "DeploymentFixComplete":
                send_terminal_message(project_id, "✅ Ingress fix applied.\n\r")
                return True
            
            tool_node_state = {**tool_state, "messages": [response]}
            node = ToolNode(gitops_tools)
            try:
                result = await node.ainvoke(tool_node_state)
                for msg in result.get("messages", []):
                    messages.append(msg)
            except Exception as e:
                logger.error(f"[{project_id}] Ingress tool error: {e}")
                messages.append(ToolMessage(
                    tool_call_id=tc["id"],
                    content=f"Error: {str(e)}",
                ))
    
    return False


# ============== MAIN ORCHESTRATOR ==============

async def sequential_deployment_fixer(state: dict) -> dict:
    """
    Main orchestrator node for the post-processing graph.
    
    Classifies errors, then fixes them sequentially:
    1. Application errors (fix source → push → wait for rebuild → rollout restart)
    2. Image creation errors (not yet handled — logged for awareness)
    3. GitOps errors (fix manifests → push to GitOps)
    4. Ingress issues (fix ingress.yaml → push to GitOps)
    
    Components with needs_fix=False are skipped (dependency-only failures).
    
    IMPORTANT: App fixes rebuild the same image tag (e.g., '1.0'). Since the
    K8s Deployment YAML doesn't change, ArgoCD sees no diff. We must force
    a `kubectl rollout restart` so K8s pulls the new image from ECR.
    """
    project_id = state.get("project_id", "")
    pod_errors = state.get("deployment_error_logs") or []
    gitops_dir = state.get("gitops_dir", "")
    retry_count = state.get("retry_count", 0)
    component_mirror_paths = state.get("component_mirror_paths") or {}
    repo_owner = state.get("repo_owner", "")
    repo_name = state.get("repo_name", "")
    namespace = project_id  # namespace == project_id
    
    send_terminal_message(project_id, f"🔄 Sequential Deployment Fixer (Attempt {retry_count + 1})...\n\r")
    
    # ---- Step 1: Classify errors (pass structured pod errors) ----
    classification = await classify_deployment_errors(pod_errors, project_id)
    
    # Filter: only process components that actually need a fix
    fixable_errors = [e for e in classification.component_errors if e.needs_fix]
    skipped_errors = [e for e in classification.component_errors if not e.needs_fix]
    
    if skipped_errors:
        send_terminal_message(
            project_id,
            f"⏭️ Skipping {len(skipped_errors)} component(s) that will self-recover: "
            f"{', '.join(e.component_name for e in skipped_errors)}\n\r",
        )
    
    # Group fixable errors by error type
    app_errors = [e for e in fixable_errors if e.error_type == "application_error"]
    image_errors = [e for e in fixable_errors if e.error_type == "image_creation_error"]
    gitops_errors = [e for e in fixable_errors if e.error_type == "gitops_fix"]
    ingress_errors = [e for e in fixable_errors if e.error_type == "ingress_issue"]
    
    any_fix_applied = False
    
    # Helper: build a readable error string for a component from structured pod data
    def _build_error_context(component_name: str) -> str:
        """Extract relevant pod error logs for a given component."""
        relevant = [pe for pe in pod_errors if pe.get("component_name") == component_name]
        if not relevant:
            # Fallback: try partial match
            relevant = [pe for pe in pod_errors if component_name in pe.get("pod_name", "")]
        parts = []
        for pe in relevant:
            parts.append(
                f"Pod: {pe.get('pod_name')}\n"
                f"Phase: {pe.get('phase')}\n"
                f"Events:\n{pe.get('events', 'N/A')}\n"
                f"Logs:\n{pe.get('logs', 'N/A')}"
            )
        return "\n\n".join(parts) if parts else "No detailed logs available."
    
    # ---- Step 2: Fix application errors ----
    if app_errors:
        send_terminal_message(
            project_id,
            f"🐛 Phase 1: Fixing {len(app_errors)} application error(s)...\n\r",
        )
        
        for ce in app_errors:
            comp_name = ce.component_name
            local_path = component_mirror_paths.get(comp_name)
            
            # Re-clone if the mirror directory doesn't exist
            if not local_path or not os.path.exists(local_path):
                send_terminal_message(
                    project_id,
                    f"📥 Re-cloning source repo for {comp_name}...\n\r",
                )
                repo_url = f"https://github.com/{repo_owner}/{repo_name}.git"
                local_path = os.path.abspath(f"temp/{repo_name}-{comp_name}")
                await AsyncGitTools.clone_repository(repo_url, local_path)
                component_mirror_paths[comp_name] = local_path
            
            error_context = _build_error_context(comp_name)
            
            result = await run_app_error_fixer(
                project_id=project_id,
                component_name=comp_name,
                error_logs=f"{ce.error_summary}\n\nDetailed pod logs:\n{error_context}",
                app_local_path=local_path,
            )
            
            if result.get("fixed"):
                any_fix_applied = True
                
                # Wait for image rebuild
                rebuild_success = await _wait_for_image_rebuild(
                    project_id=project_id,
                    component_name=comp_name,
                    repo_owner=repo_owner,
                    repo_name=repo_name,
                    local_path=local_path,
                )
                
                if rebuild_success:
                    # CRITICAL: The image was rebuilt with the SAME tag (e.g., '1.0').
                    # ArgoCD sees no diff in the GitOps repo since the image URL hasn't changed.
                    # We must force K8s to pull the new image via rollout restart.
                    send_terminal_message(
                        project_id,
                        f"🔄 Forcing rollout restart for {comp_name} to pull new image...\n\r",
                    )
                    subprocess.run(
                        ["kubectl", "rollout", "restart", f"deployment/{comp_name}", "-n", namespace],
                        check=False, capture_output=True,
                    )
                else:
                    send_terminal_message(
                        project_id,
                        f"⚠️ Image rebuild failed for {comp_name} after app fix. Will continue with other fixes.\n\r",
                    )
    
    # ---- Step 3: Fix image creation errors ----
    if image_errors:
        send_terminal_message(
            project_id,
            f"🏗️ Phase 2: {len(image_errors)} image build error(s) detected. "
            f"These require CI/CD pipeline fixes and will be retried on next build cycle.\n\r",
        )
        for ce in image_errors:
            send_terminal_message(
                project_id,
                f"   ⚠️ {ce.component_name}: {ce.error_summary}\n\r",
            )
    
    # ---- Step 4: Fix GitOps errors ----
    if gitops_errors:
        send_terminal_message(
            project_id,
            f"📝 Phase 3: Fixing {len(gitops_errors)} GitOps manifest error(s)...\n\r",
        )
        
        gitops_fixed = await _fix_gitops_errors(project_id, gitops_errors, gitops_dir)
        if gitops_fixed:
            any_fix_applied = True
    
    # ---- Step 5: Fix ingress issues ----
    if ingress_errors:
        send_terminal_message(
            project_id,
            f"🌐 Phase 4: Fixing {len(ingress_errors)} ingress issue(s)...\n\r",
        )
        
        ingress_fixed = await _fix_ingress_errors(project_id, ingress_errors, gitops_dir)
        if ingress_fixed:
            any_fix_applied = True
    
    # ---- Step 6: Trigger ArgoCD sync for ANY fix ----
    # Even app error fixes need this: the image tag stays the same (e.g., '1.0'),
    # so ArgoCD won't detect a change unless we force a refresh.
    if any_fix_applied:
        send_terminal_message(project_id, "🔄 Triggering ArgoCD sync after fixes...\n\r")
        app_name = f"app-{project_id}"
        subprocess.run(
            [
                "kubectl", "annotate", "application", app_name,
                "-n", "argocd",
                "argocd.argoproj.io/refresh=hard",
                "--overwrite",
            ],
            check=False,
            capture_output=True,
        )
        # Give ArgoCD time to sync before re-monitoring
        await asyncio.sleep(15)
    
    # ---- Return ----
    if any_fix_applied:
        send_terminal_message(project_id, "✅ Fixes applied. Re-monitoring deployment...\n\r")
    else:
        send_terminal_message(project_id, "⚠️ No fixes could be applied in this cycle.\n\r")
    
    return {
        "retry_count": retry_count + 1,
        "deployment_status": "retrying",
        "component_mirror_paths": component_mirror_paths,
        "classified_errors": {
            "app_errors": len(app_errors),
            "image_errors": len(image_errors),
            "gitops_errors": len(gitops_errors),
            "ingress_errors": len(ingress_errors),
            "skipped": len(skipped_errors),
        },
    }
