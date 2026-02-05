from langgraph.graph import StateGraph, END  
from state import AgentState
from agents.repo_analyst import (
    repo_analysis_agent, 
    repo_analysis_tool_node, 
    finalize_analysis, 
    check_analysis_finish
)
from agents.docker_agent import docker_node
from agents.pipeline_agent import pipeline_node
from agents.monitor_agent import monitor_build_node

# Build Graph
workflow = StateGraph(AgentState)

# Nodes
workflow.add_node("repo_analysis_agent", repo_analysis_agent)
workflow.add_node("repo_analysis_tool", repo_analysis_tool_node)
workflow.add_node("finalize_analysis", finalize_analysis)
workflow.add_node("write_docker", docker_node)
workflow.add_node("write_pipeline", pipeline_node)
workflow.add_node("monitor", monitor_build_node)
workflow.add_node("failed", lambda x: {"build_status": "analysis_failed"})

# Edges
workflow.set_entry_point("repo_analysis_agent")

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
workflow.add_edge("finalize_analysis", "write_docker")
workflow.add_edge("write_docker", "write_pipeline")
workflow.add_edge("write_pipeline", "monitor")
workflow.add_edge("monitor", END)
workflow.add_edge("failed", END)

app = workflow.compile()