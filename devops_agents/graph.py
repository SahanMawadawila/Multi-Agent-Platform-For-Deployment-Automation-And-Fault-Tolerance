import time
from langgraph.graph import StateGraph, END  
from state import AgentState, PostProcessingState
from agents.docker_agent import docker_writing_agent
from agents.pipeline_agent import pipeline_writing_agent
from agents.monitor_agent import build_monitor_agent
from agents.error_fixing_agent import (
    error_analyzer_agent,
    error_planner_agent,
    error_fixing_agent,
    error_fixing_tool_node,
    check_fix_complete,
    finalize_fix
)
from agents.k8s_architect_agent import k8s_architect_agent
from agents.ingress_networking import generate_ingress
from agents.gitops_argocd_agent import gitops_argocd_agent
from agents.deployment_monitor_agent import deployment_monitor_agent
from app.kafka_build_producer import send_build_event

# ==========================================================
#  COMPONENT GRAPH  (per-component, runs N times in parallel)
# ==========================================================

def check_build_status(state):
    """Route based on build status after monitoring."""
    build_status = state.get("build_status", "")
    retry_count = state.get("retry_count", 0)
    plan = state.get("error_fixing_plan", [])
    step_idx = state.get("current_step_index", 0)
    
    if build_status == "success":
        return "success"
    
    if build_status == "failed":
        if retry_count >= 3:
            return "give_up"
        
        if plan and step_idx < len(plan):
            return "continue_fix"
        else:
            return "start_analysis"
            
    return "give_up"

# Build the component workflow
component_workflow = StateGraph(AgentState)

# Nodes - Docker & Pipeline
component_workflow.add_node("docker_writing_agent", docker_writing_agent)
component_workflow.add_node("pipeline_writing_agent", pipeline_writing_agent)

# Nodes - Build Monitor
component_workflow.add_node("build_monitor_agent", build_monitor_agent)

# Nodes - Error Planning & Fixing
component_workflow.add_node("error_analyzer_agent", error_analyzer_agent)
component_workflow.add_node("error_planner_agent", error_planner_agent)
component_workflow.add_node("error_fixing_agent", error_fixing_agent)
component_workflow.add_node("error_fixing_tool", error_fixing_tool_node)
component_workflow.add_node("finalize_fix", finalize_fix)

# Nodes - K8s Manifest Generation
component_workflow.add_node("k8s_architect_agent", k8s_architect_agent)

# Nodes - Build Failed (only for build failures within this component)
def mark_component_failed(state):
    """Mark this component's build as failed."""
    error_logs = state.get("build_error_logs", "") or state.get("monitor_logs", "") or "Build failed"
    if len(error_logs) > 1000:
        error_logs = error_logs[:1000] + "..."
    return {"build_status": "failed"}

component_workflow.add_node("failed", mark_component_failed)

# Edges
component_workflow.set_entry_point("docker_writing_agent")

# Docker -> Pipeline -> Build Monitor
component_workflow.add_edge("docker_writing_agent", "pipeline_writing_agent")
component_workflow.add_edge("pipeline_writing_agent", "build_monitor_agent")

# Build Monitor Routing
component_workflow.add_conditional_edges(
    "build_monitor_agent",
    check_build_status,
    {
        "success": "k8s_architect_agent",
        "continue_fix": "error_fixing_agent",
        "start_analysis": "error_analyzer_agent",
        "give_up": "failed"
    }
)

# Error Planning Flow
component_workflow.add_edge("error_analyzer_agent", "error_planner_agent")
component_workflow.add_edge("error_planner_agent", "error_fixing_agent")

# Error Execution Flow
component_workflow.add_conditional_edges(
    "error_fixing_agent",
    check_fix_complete,
    {
        "error_fixing_tool": "error_fixing_tool",
        "error_fixing_agent": "error_fixing_agent",
        "fix_complete": "finalize_fix"
    }
)
component_workflow.add_edge("error_fixing_tool", "error_fixing_agent")
component_workflow.add_edge("finalize_fix", "build_monitor_agent")

# K8s Architect -> END
component_workflow.add_edge("k8s_architect_agent", END)

# Failed -> END
component_workflow.add_edge("failed", END)

# Compile
component_graph = component_workflow.compile()


# ==========================================================
#  POST-PROCESSING GRAPH  (runs once after all components)
# ==========================================================

def check_deployment_status(state):
    """Route based on deployment status."""
    status = state.get("deployment_status", "")
    if status == "success":
        return "success"
    return "failed"

def mark_deployment_success(state):
    """Send success event."""
    access_url = state.get("access_url", "")
    gitops_commit_id = state.get("gitops_commit_id", "")
    start_time = state.get("start_time")
    duration = int(time.time() - start_time) if start_time else None
    send_build_event(
        state["project_id"], 
        state["build_id"], 
        "success",
        details={
            "access_url": access_url,
            "is_current": True,
            "gitops_commit_id": gitops_commit_id,
            "duration": duration
        }
    )
    return {"deployment_status": "success", "access_url": access_url}

def mark_deployment_failed(state):
    """Send failure event."""
    start_time = state.get("start_time")
    duration = int(time.time() - start_time) if start_time else None
    send_build_event(
        state["project_id"], 
        state["build_id"], 
        "failed", 
        details={
            "error": "Deployment failed",
            "duration": duration
        }
    )
    return {"deployment_status": "failed"}

# Build the post-processing workflow
pp_workflow = StateGraph(PostProcessingState)

pp_workflow.add_node("ingress_generator", generate_ingress)
pp_workflow.add_node("gitops_argocd", gitops_argocd_agent)
pp_workflow.add_node("deployment_monitor", deployment_monitor_agent)
pp_workflow.add_node("success", mark_deployment_success)
pp_workflow.add_node("failed", mark_deployment_failed)

# Edges
pp_workflow.set_entry_point("ingress_generator")
pp_workflow.add_edge("ingress_generator", "gitops_argocd")
pp_workflow.add_edge("gitops_argocd", "deployment_monitor")

pp_workflow.add_conditional_edges(
    "deployment_monitor",
    check_deployment_status,
    {
        "success": "success",
        "failed": "failed"
    }
)

pp_workflow.add_edge("success", END)
pp_workflow.add_edge("failed", END)

# Compile
post_processing_graph = pp_workflow.compile()
