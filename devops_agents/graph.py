import time
from langgraph.graph import StateGraph, END  
from state import AgentState
from agents.repo_analyst import (
    repo_analysis_agent, 
    repo_analysis_tool_node, 
    finalize_analysis, 
    check_analysis_finish
)
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
from agents.deployment_monitor_agent import deployment_monitor_agent
from app.kafka_build_producer import send_build_event

# Monorepo Imports
from agents.monorepo_detector_agent import monorepo_detector_agent
from agents.monorepo_coordinator import (
    prepare_component_analysis, 
    save_component_analysis, 
    check_analysis_loop,
    prepare_docker_generation, 
    save_docker_result, 
    check_docker_loop,
    check_monorepo_enabled
)

# ============== ROUTING FUNCTIONS ==============
def check_build_status(state):
    """Route based on build status after monitoring."""
    build_status = state.get("build_status", "")
    retry_count = state.get("retry_count", 0)
    plan = state.get("error_fixing_plan", [])
    step_idx = state.get("current_step_index", 0)
    
    if build_status == "success":
        return "success"
    
    # If build failed
    if build_status == "failed":
        if retry_count >= 3:
            return "give_up"
        
        # If we have a plan in progress, continue to next step
        if plan and step_idx < len(plan):
            return "continue_fix"
        else:
            # No plan yet or plan finished but still failing -> start fresh analysis
            return "start_analysis"
            
    return "give_up"

def check_deployment_status(state):
    """Route based on deployment status."""
    status = state.get("deployment_status", "")
    if status == "success":
        return "success"
    else:
        return "failed"

def check_plan_exists(state):
    """Check if we already have a plan to follow."""
    plan = state.get("error_fixing_plan", [])
    step_idx = state.get("current_step_index", 0)
    if plan and step_idx < len(plan):
        return "error_fixing_agent"
    return "error_analyzer_agent"

# ============== BUILD GRAPH ==============
workflow = StateGraph(AgentState)

# Nodes - Monorepo Setup
workflow.add_node("monorepo_detector_agent", monorepo_detector_agent)

# Nodes - Coordinator
workflow.add_node("prepare_component_analysis", prepare_component_analysis)
workflow.add_node("save_component_analysis", save_component_analysis)
workflow.add_node("prepare_docker_generation", prepare_docker_generation)
workflow.add_node("save_docker_result", save_docker_result)

# Nodes - Repo Analysis
workflow.add_node("repo_analysis_agent", repo_analysis_agent)
workflow.add_node("repo_analysis_tool", repo_analysis_tool_node)
workflow.add_node("finalize_analysis", finalize_analysis)

# Nodes - Docker & Pipeline
workflow.add_node("docker_writing_agent", docker_writing_agent)
workflow.add_node("pipeline_writing_agent", pipeline_writing_agent)

# Nodes - Build Monitor
workflow.add_node("build_monitor_agent", build_monitor_agent)

# Nodes - Error Planning & Fixing
workflow.add_node("error_analyzer_agent", error_analyzer_agent)
workflow.add_node("error_planner_agent", error_planner_agent)
workflow.add_node("error_fixing_agent", error_fixing_agent)
workflow.add_node("error_fixing_tool", error_fixing_tool_node)
workflow.add_node("finalize_fix", finalize_fix)

# Nodes - K8s Architect
workflow.add_node("k8s_architect_agent", k8s_architect_agent)
workflow.add_node("deployment_monitor_agent", deployment_monitor_agent)

# Nodes - Terminal States
def mark_deployment_success(state):
    """Send success event with access_url, is_current flag, gitops_commit_id, and duration."""
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
    return {"build_status": "success", "access_url": access_url}

def mark_deployment_failed(state):
    """Send failure event with error details and duration."""
    error_logs = state.get("build_error_logs", "") or state.get("monitor_logs", "") or "Deployment failed"
    # Truncate details if they are too long for Kafka message
    if len(error_logs) > 1000:
        error_logs = error_logs[:1000] + "..."
    start_time = state.get("start_time")
    duration = int(time.time() - start_time) if start_time else None
    send_build_event(
        state["project_id"], 
        state["build_id"], 
        "failed", 
        details={
            "error": error_logs,
            "duration": duration
        }
    )
    return {"build_status": "failed"}

workflow.add_node("success", mark_deployment_success)
workflow.add_node("failed", mark_deployment_failed)

# ============== EDGES ==============
# Main Entry Point
workflow.set_entry_point("monorepo_detector_agent")

# Monorepo -> Analysis Loop
workflow.add_conditional_edges(
    "monorepo_detector_agent",
    check_monorepo_enabled,
    {
        "prepare_component_analysis": "prepare_component_analysis"
    }
)

# Analysis Loop Flow
workflow.add_edge("prepare_component_analysis", "repo_analysis_agent")

# Repo Analysis standard flow
workflow.add_conditional_edges(
    "repo_analysis_agent",
    check_analysis_finish,
    {
        "repo_analysis_tool": "repo_analysis_tool",
        "finalize_analysis": "finalize_analysis",
        "repo_analysis_agent": "repo_analysis_agent",
        "failed": "failed"
    }
)
workflow.add_edge("repo_analysis_tool", "repo_analysis_agent")

# Loop Back or Continue
workflow.add_edge("finalize_analysis", "save_component_analysis")

workflow.add_conditional_edges(
    "save_component_analysis",
    check_analysis_loop,
    {
        "prepare_component_analysis": "prepare_component_analysis", # Loop back
        "docker_coordinator": "prepare_docker_generation"           # Proceed to next phase
    }
)

# Docker Loop Flow
workflow.add_edge("prepare_docker_generation", "docker_writing_agent")
workflow.add_edge("docker_writing_agent", "save_docker_result")

workflow.add_conditional_edges(
    "save_docker_result",
    check_docker_loop,
    {
        "prepare_docker_generation": "prepare_docker_generation", # Loop back
        "pipeline_writing_agent": "pipeline_writing_agent"        # Proceed to Pipeline
    }
)

# Pipeline -> Monitor
workflow.add_edge("pipeline_writing_agent", "build_monitor_agent")

# Build Monitor Routing
workflow.add_conditional_edges(
    "build_monitor_agent",
    check_build_status,
    {
        "success": "success", # Stop after build for testing
        "continue_fix": "error_fixing_agent",
        "start_analysis": "error_analyzer_agent",
        "give_up": "failed"
    }
)

# Error Planning Flow
workflow.add_edge("error_analyzer_agent", "error_planner_agent")
workflow.add_edge("error_planner_agent", "error_fixing_agent")

# Error Execution Flow
workflow.add_conditional_edges(
    "error_fixing_agent",
    check_fix_complete,
    {
        "error_fixing_tool": "error_fixing_tool",
        "error_fixing_agent": "error_fixing_agent",
        "fix_complete": "finalize_fix"
    }
)
workflow.add_edge("error_fixing_tool", "error_fixing_agent")
workflow.add_edge("finalize_fix", "build_monitor_agent")

workflow.add_edge("k8s_architect_agent", "deployment_monitor_agent")

workflow.add_conditional_edges(
    "deployment_monitor_agent",
    check_deployment_status,
    {
        "success": "success",
        "failed": "failed"
    }
)

# Terminal States
workflow.add_edge("success", END)
workflow.add_edge("failed", END)

app = workflow.compile()
