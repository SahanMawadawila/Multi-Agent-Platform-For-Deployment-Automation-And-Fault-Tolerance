from typing import TypedDict, List, Optional, Annotated
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
""" 
class DeploymentState(TypedDict):
    repository_url: str
    language: str
    detected_port:str
    dockerfile_content: Optional[str]
    k8s_manifest: dict
    build_status: str
    deploy_status: str
    error_logs: List[str]
    retry_count: int
    messages: Annotated[List[str], operator.add]  """

class RepoAnalysisOutput(BaseModel):
    """
    Structured output that the agent MUST provide to finish the task.
    """
    language: str = Field(..., description="Programming language detected (e.g., node, python)")
    framework: str = Field(..., description="Framework used (e.g., express, fastify, django)")
    port: int = Field(..., description="Port number the application listens on")
    build_command: str = Field(..., description="Command to build the app (e.g., npm run build)")
    run_command: str = Field(..., description="Command to start the app (e.g., npm start)")
    env_variables: List[str] = Field(..., description="List of environment variable KEYS required (e.g., DB_URL)")

class AgentState(TypedDict):
    """
    The memory passed between nodes in the graph.
    """
    repo_url: str  # The input URL from Kafka
    local_path: str  # Where we cloned the repo on disk
    file_list: List[str]  # List of files in the repo
    
    # 'add_messages' ensures we keep the history of Tool Calls (Looping memory)
    messages: Annotated[List, add_messages] 
    
    # The final output. Optional until the agent finishes.
    final_analysis: Optional[RepoAnalysisOutput]

    loop_count: int