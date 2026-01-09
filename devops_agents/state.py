# state.py
from typing import TypedDict, List, Optional, Annotated, Dict, Any
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

class RepoAnalysisOutput(BaseModel):
    """
    Structured output from the analysis phase.
    """
    language: str = Field(..., description="Programming language (node, python)")
    version: str = Field(..., description="Runtime version (e.g. 18)")
    package_manager: str = Field(..., description="npm, yarn, pnpm")
    port: int = Field(..., description="Application port")
    build_command: str = Field(..., description="Build command if exists")
    run_command: str = Field(..., description="Start command")
    env_variables: List[str] = Field(..., description="Required Env Var Keys")
    # Added for robustness
    has_lockfile: bool = Field(False, description="If a lockfile was found")
    framework: Optional[str] = Field(None, description="Detected framework (next, nest, express)")

class AgentState(TypedDict):
    """
    The memory passed between nodes in the graph.
    """
    project_id: str  # <--- ADDED THIS
    repo_url: str
    local_path: str
    file_list: List[str]
    repo_owner: str
    repo_name: str
    
    messages: Annotated[List, add_messages] 
    
    final_analysis: Optional[RepoAnalysisOutput] # Replace with your actual class
    build_status: Optional[str]
    loop_count: int