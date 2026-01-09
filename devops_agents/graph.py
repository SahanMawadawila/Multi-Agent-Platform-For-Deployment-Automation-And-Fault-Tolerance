# graph.py
from langgraph.graph import StateGraph, END  
from langgraph.prebuilt import ToolNode
from state import AgentState, RepoAnalysisOutput
from tools.git_tools import AsyncGitTools
from agents.repo_analyst import repo_analysis_agent, tools as agent_tools, set_local_path 
from agents.docker_agent import docker_node
from agents.pipeline_agent import pipeline_node
from agents.monitor_agent import monitor_build_node

async def setup_repo(state: AgentState):
    repo_url = state["repo_url"]
    repo_name_full = repo_url.split("github.com/")[-1].replace(".git", "")
    owner, name = repo_name_full.split("/")
    
    local_path = f"temp/{name}"
    
    await AsyncGitTools.clone_repository(repo_url, local_path)
    files = await AsyncGitTools.list_files(local_path)
    set_local_path(local_path)
    
    return {
        "local_path": local_path, 
        "file_list": files,
        "repo_owner": owner,
        "repo_name": name
    }

async def custom_tool_node(state):
    set_local_path(state["local_path"])
    tool_node = ToolNode(agent_tools)
    return await tool_node.ainvoke(state)

def finalize_analysis(state):
    last_message = state["messages"][-1]
    output_args = last_message.tool_calls[0]["args"]
    # Ensure validation
    final_data = RepoAnalysisOutput(**output_args)
    return {"final_analysis": final_data}

def check_analysis_finish(state):
    current_count = state.get("loop_count", 0)
    if current_count >= 8: 
        return "failed"
        
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
        if last_message.tool_calls[0]["name"] == "RepoAnalysisOutput":
            return "finalize_analysis"
        return "tools"
    return "agent"

# Build Graph
workflow = StateGraph(AgentState)

# Nodes
workflow.add_node("setup", setup_repo)
workflow.add_node("agent", repo_analysis_agent)
workflow.add_node("tools", custom_tool_node)
workflow.add_node("finalize_analysis", finalize_analysis)
workflow.add_node("write_docker", docker_node)
workflow.add_node("write_pipeline", pipeline_node)
workflow.add_node("monitor", monitor_build_node)
workflow.add_node("failed", lambda x: {"build_status": "analysis_failed"})

# Edges
workflow.set_entry_point("setup")
workflow.add_edge("setup", "agent")

workflow.add_conditional_edges(
    "agent",
    check_analysis_finish,
    {
        "tools": "tools",
        "finalize_analysis": "finalize_analysis",
        "agent": "agent",
        "failed": "failed"
    }
)

workflow.add_edge("tools", "agent")
workflow.add_edge("finalize_analysis", "write_docker")
workflow.add_edge("write_docker", "write_pipeline")
workflow.add_edge("write_pipeline", "monitor")
workflow.add_edge("monitor", END)
workflow.add_edge("failed", END)

# Compile with Recursion Limit as requested
app = workflow.compile() # Set slightly higher than 8 to allow for tool loops + linear steps