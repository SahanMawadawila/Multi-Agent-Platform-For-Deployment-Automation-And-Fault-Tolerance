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
    error_fixing_agent,
    error_fixing_tool_node,
    check_fix_complete,
    finalize_fix
)

# ============== ROUTING FUNCTIONS ==============
def check_build_status(state):
    """Route based on build status after monitoring."""
    build_status = state.get("build_status", "")
    retry_count = state.get("retry_count", 0)
    
    if build_status == "success":
        return "success"
    elif build_status == "failed" and retry_count < 3:
        return "needs_fix"
    else:
        return "give_up"

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

# Nodes - Error Fixing
workflow.add_node("error_fixing_agent", error_fixing_agent)
workflow.add_node("error_fixing_tool", error_fixing_tool_node)
workflow.add_node("finalize_fix", finalize_fix)

# Nodes - Terminal States
workflow.add_node("success", lambda x: {"build_status": "success"})
workflow.add_node("failed", lambda x: {"build_status": "failed"})

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
        "success": "success",
        "needs_fix": "error_fixing_agent",
        "give_up": "failed"
    }
)

# Error Fixing Flow
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

# Terminal States
workflow.add_edge("success", END)
workflow.add_edge("failed", END)

app = workflow.compile()