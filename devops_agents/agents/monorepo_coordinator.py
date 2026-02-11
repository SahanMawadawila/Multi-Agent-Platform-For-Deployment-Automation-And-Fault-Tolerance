from state import AgentState
from app.kafka_terminal_producer import send_terminal_message
from langgraph.graph import END
from langchain_core.messages import RemoveMessage

def get_next_unanalyzed_component_index(state: AgentState) -> int:
    """Finds the index of the first component that hasn't been analyzed yet."""
    components = state.get("components", [])
    for i, comp in enumerate(components):
        if comp.get("analysis") is None:
            return i
    return -1

def get_next_unbuilt_docker_component_index(state: AgentState) -> int:
    """Finds the index of the first component that doesn't have a Dockerfile content generated."""
    components = state.get("components", [])
    for i, comp in enumerate(components):
        if comp.get("dockerfile_content") is None:
            return i
    return -1

async def prepare_component_analysis(state: AgentState):
    """
    Prepares the state for the next component's analysis by:
    1. Selecting the component files.
    2. Resetting analysis messages and results.
    """
    idx = get_next_unanalyzed_component_index(state)
    # If no component found, this node shouldn't have been called, but handle gracefully
    if idx == -1:
        return {} 

    component = state["components"][idx]
    project_id = state.get("project_id", "")
    
    send_terminal_message(project_id, f"🔍 [Monorepo] Switching context to component: {component['name']} ({component['path']})\n\r")
    
    # Clear previous messages to ensure fresh context for this component
    messages = state.get("messages", [])
    result = {
        "file_list": component["file_list"],
        "analyzed_repository_details": None, 
    }
    
    # Generate delete operations for all existing messages with IDs
    delete_ops = [RemoveMessage(id=m.id) for m in messages if hasattr(m, 'id') and m.id]
    if delete_ops:
        result["messages"] = delete_ops
        
    return result

async def save_component_analysis(state: AgentState):
    """
    Captures the RepoAnalysisOutput from the shared agent and saves it 
    to the active component in the component list.
    """
    analysis = state.get("analyzed_repository_details")
    components = state.get("components", [])
    project_id = state.get("project_id", "")
    
    # Identify which component we just processed
    # Since we process sequentially, it's the first one without analysis
    idx = get_next_unanalyzed_component_index(state)
    
    if idx == -1:
        # Should not happen if logic is correct
        send_terminal_message(project_id, "⚠️ Warning: Could not match analysis to a component.\n\r")
        return {}

    # Update component
    # We must copy to avoid mutating the state in place unexpectedly, though TypedDict behaves like dict
    updated_comp = components[idx].copy()
    updated_comp["analysis"] = analysis
    
    components[idx] = updated_comp
    
    send_terminal_message(project_id, f"✅ Analyzed {updated_comp['name']}: {analysis.project_type} project.\n\r")
    
    return {
        "components": components,
        "analyzed_repository_details": None # Clear it to avoid confusion in next steps? Or keep as last valid?
                                            # Better to clear/ignore in next 'prepare' step.
    }

def check_analysis_loop(state: AgentState):
    """
    Router:
    - If there are more unanalyzed components -> 'prepare_component_analysis'
    - Else -> Proceed to Docker Generation Loop
    """
    idx = get_next_unanalyzed_component_index(state)
    if idx != -1:
        return "prepare_component_analysis"
    return "docker_coordinator" # Transitions to the next phase

def check_monorepo_enabled(state: AgentState):
    """
    Router from MonorepoDetector:
    - If components list > 0 (or >1?), go to Analysis Loop.
    - If list is empty/single -> standard flow (skip loop).
    
    Actually, if we standardize on 'components' list even for single repo (size=1), 
    we can use the loop for everything! 
    The MonorepoDetector creates a single component for normal repos.
    So we can ALWAYS go to the loop. 
    """
    # Simply route to the start of the analysis loop
    return "prepare_component_analysis"

async def prepare_docker_generation(state: AgentState):
    """
    Prepares state for Docker agent.
    1. Selects component.
    2. Injects 'analyzed_repository_details' from component.
    3. Sets 'docker_output_path' to component path.
    """
    idx = get_next_unbuilt_docker_component_index(state)
    if idx == -1:
        return {}
        
    component = state["components"][idx]
    project_id = state.get("project_id", "")
    
    # Calculate docker path
    # If path is ".", docker path is "Dockerfile"
    # If path is "backend", docker path is "backend/Dockerfile"
    docker_path = "Dockerfile"
    if component["path"] != ".":
        docker_path = f"{component['path']}/Dockerfile"
        
    send_terminal_message(project_id, f"🐋 [Monorepo] Generating Dockerfile for: {component['name']}\n\r")
    
    return {
        "analyzed_repository_details": component["analysis"],
        "docker_output_path": docker_path
    }

async def save_docker_result(state: AgentState):
    """
    Captures generated Dockerfile content and saves to component.
    """
    docker_content = state.get("dockerfile_content")
    components = state.get("components", [])
    project_id = state.get("project_id", "")
    
    idx = get_next_unbuilt_docker_component_index(state)
    if idx == -1:
        return {}
        
    updated_comp = components[idx].copy()
    updated_comp["dockerfile_content"] = docker_content
    components[idx] = updated_comp
    
    return {
        "components": components,
        "dockerfile_content": None # Clear for next
    }

def check_docker_loop(state: AgentState):
    """
    Router:
    - If more components need dockerfiles -> 'prepare_docker_generation'
    - Else -> 'pipeline_writing_agent'
    """
    idx = get_next_unbuilt_docker_component_index(state)
    if idx != -1:
        return "prepare_docker_generation"
    return "pipeline_writing_agent"
