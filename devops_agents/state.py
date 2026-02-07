# state.py
from typing import TypedDict, List, Optional, Annotated
from langgraph.graph.message import add_messages
from agents.repo_analyst import RepoAnalysisOutput

class AgentState(TypedDict):
    project_id: str  
    local_path: str
    file_list: List[str]
    repo_owner: str
    repo_name: str
    messages: Annotated[List, add_messages] 
    analyzed_repository_details: Optional[RepoAnalysisOutput] 
    build_status: Optional[str]
    build_error_logs: Optional[str]
    retry_count: int
    error_fixing_messages: Annotated[List, add_messages]
    k8s_status: Optional[str]
    image_url: Optional[str]
    deployment_status: Optional[str]
    access_url: Optional[str]
    monitor_logs: Optional[str]