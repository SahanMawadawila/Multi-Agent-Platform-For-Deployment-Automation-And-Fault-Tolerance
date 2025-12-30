# graph.py
from langgraph.graph import StateGraph, END  # Graph components
from langgraph.prebuilt import ToolNode, tools_condition  # Prebuilt logic for tool calling
from state import AgentState, RepoAnalysisOutput  # State definition
from tools.git_tools import AsyncGitTools  # Git tools
from agents.repo_analyst import repo_analysis_agent, tools as agent_tools, set_local_path  # Agent logic
import json  # Parsing JSON

# --- Node 1: Setup Node ---
async def setup_repo(state: AgentState):
    """
    Clones the repo and lists files before the agent starts.
    """
    repo_url = state["repo_url"]
    # Create a unique local path based on repo name to avoid collisions
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    local_path = f"temp/{repo_name}"
    
    # Async clone
    await AsyncGitTools.clone_repository(repo_url, local_path)
    # Async list files
    files = await AsyncGitTools.list_files(local_path)
    
    # Set the local path for tools to use
    set_local_path(local_path)
    
    # Update state with path and file list
    return {"local_path": local_path, "file_list": files}

# --- Node 2: Custom Tool Node ---
async def custom_tool_node(state):
    """Execute tools with the local path context."""
    # Ensure local_path is set for tools
    set_local_path(state["local_path"])
    
    # Create and invoke the standard ToolNode
    tool_node = ToolNode(agent_tools)
    return await tool_node.ainvoke(state)

# --- Conditional Logic: Check if finished ---
# graph.py

def check_finish(state):
    """
    Decides where to go next: Tools, Finish, or FORCE STOP.
    """
    # 1. Check Safety Limit
    current_count = state.get("loop_count", 0)
    if current_count >= 5: # <--- SET YOUR LIMIT (e.g., 10 steps)
        print(f"🚨 KILLING PROCESS: Infinite Loop Detected for {state['repo_url']}")
        return "failed" # Route to a failure node
        
    last_message = state["messages"][-1]
    
    # 2. Standard Logic
    if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
        tool_name = last_message.tool_calls[0]["name"]
        if tool_name == "RepoAnalysisOutput":
            return "finalize"
        return "tools"
        
    return "agent"

def failed_node(state):
    print("❌ Task Failed: Agent got stuck in a loop.")
    # You could send a Kafka message here saying "Job Failed"
    return {"final_analysis": None} # Return empty/None to signal failure

# --- Node 3: Finalizer ---
def finalize_node(state):
    """Extracts the structured output from the tool call arguments."""
    last_message = state["messages"][-1]
    # Parse the arguments provided by the LLM
    output_args = last_message.tool_calls[0]["args"]
    # Validate using Pydantic
    final_data = RepoAnalysisOutput(**output_args)
    return {"final_analysis": final_data}

# --- Build the Graph ---
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("setup", setup_repo)
workflow.add_node("agent", repo_analysis_agent)
workflow.add_node("tools", custom_tool_node)
workflow.add_node("finalize", finalize_node)
workflow.add_node("failed", failed_node)

# Set Entry Point
workflow.set_entry_point("setup")

# Add Edges
workflow.add_edge("setup", "agent")

# Add Conditional Edge (The Loop)
workflow.add_conditional_edges(
    "agent",
    check_finish,
    {
        "tools": "tools",       # Go read files
        "finalize": "finalize", # Done
        "agent": "agent"        # Retry (fallback)
        ,"failed": "failed"      # Safety kill switch
    }
)

# Loop back from tools to agent
workflow.add_edge("tools", "agent")
workflow.add_edge("finalize", END)
workflow.add_edge("failed", END)

# Compile
app = workflow.compile()