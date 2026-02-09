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
# Nodes - K8s Architect
workflow.add_node("k8s_architect_agent", k8s_architect_agent)
workflow.add_node("deployment_monitor_agent", deployment_monitor_agent)

# Nodes - Terminal States
def mark_deployment_success(state):
    """Send success event with access_url and is_current flag."""
    access_url = state.get("access_url", "")
    send_build_event(
        state["project_id"], 
        state["build_id"], 
        "success",
        details={
            "access_url": access_url,
            "is_current": True  # Mark this build as the current deployment
        }
    )
    return {"build_status": "success", "access_url": access_url}

def mark_deployment_failed(state):
    """Send failure event with error details."""
    error_logs = state.get("build_error_logs", "") or state.get("monitor_logs", "") or "Deployment failed"
    # Truncate details if they are too long for Kafka message
    if len(error_logs) > 1000:
        error_logs = error_logs[:1000] + "..."
    send_build_event(state["project_id"], state["build_id"], "failed", details=error_logs)
    return {"build_status": "failed"}

workflow.add_node("success", mark_deployment_success)
workflow.add_node("failed", mark_deployment_failed)

# ============== EDGES ==============
workflow.set_entry_point("repo_analysis_agent")

# Repo Analysis Flow
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
workflow.add_edge("finalize_analysis", "docker_writing_agent")

# Docker & Pipeline Flow
workflow.add_edge("docker_writing_agent", "pipeline_writing_agent")
workflow.add_edge("pipeline_writing_agent", "build_monitor_agent")

# Build Monitor Routing
workflow.add_conditional_edges(
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