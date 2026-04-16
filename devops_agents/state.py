# state.py
from typing import TypedDict, List, Optional, Annotated, Dict, Any
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    project_id: str  
    build_id: str # The unique ID for this specific build/run
    build_version: str  # Version string (e.g., "1.0", "1.1")
    local_path: str
    file_list: List[str]
    repo_owner: str
    repo_name: str
    messages: Annotated[List, add_messages] 
    analyzed_repository_details: Optional[Dict[str, Any]]
    build_status: Optional[str]
    build_error_logs: Optional[str]
    retry_count: int
    error_fixing_messages: Annotated[List, add_messages]
    k8s_status: Optional[str]
    image_url: Optional[str]
    deployment_status: Optional[str]
    access_url: Optional[str]
    monitor_logs: Optional[str]
    gitops_commit_id: Optional[str]  # GitOps repo commit SHA for rollback
    error_fixing_plan: Optional[List[dict]] # List of { "id": int, "task": str, "status": str }
    current_step_index: int
    analysis_results: Optional[str]
    start_time: Optional[float]  # time.time() when job started, for duration calc
    component_name: Optional[str]  # Component name for multi-project repos (e.g., "frontend")
    component_path: Optional[str]  # Component path relative to repo root (e.g., "frontend")
    component_spec: Optional[Dict[str, Any]]  # Plan-driven component payload (application)
    branch_name: Optional[str]  # Branch to push to (used for multi-project repos)
    overridden_envs: Optional[dict]  # {"KEY": "value"} — env vars injected into K8s Deployment
    role: Optional[str]  # "frontend", "backend", "worker", "api-gateway"
    api_path_prefix: Optional[str]  # "/api", "/auth" — for Ingress path rules
    is_multi_project: Optional[bool]  # True if repo has multiple components


class PostProcessingState(TypedDict):
    """State for the post-processing graph (runs once after all component graphs)."""
    project_id: str
    build_id: str
    start_time: Optional[float]
    is_multi_project: bool
    # List of component dicts: [{name, app_name, api_path_prefix, port, health_check_path}]
    components: list
    ingress_config: Optional[dict]
    gitops_commit_id: Optional[str]
    access_url: Optional[str]
    deployment_status: Optional[str]