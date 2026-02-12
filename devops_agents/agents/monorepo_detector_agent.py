from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from config.settings import settings
from state import AgentState
from app.kafka_terminal_producer import send_terminal_message
from pydantic import BaseModel, Field
from typing import List

class ComponentSchema(BaseModel):
    name: str = Field(..., description="Name of the component (e.g., 'backend', 'frontend', 'auth-service')")
    path: str = Field(..., description="Path to the component root relative to repo root (e.g., '.', 'services/backend')")
    type: str = Field(..., description="Project type: 'node', 'spring-boot', 'python', 'static', 'other'")

class MonorepoDetectionOutput(BaseModel):
    is_monorepo: bool = Field(..., description="True if multiple deployable components are detected")
    components: List[ComponentSchema] = Field(..., description="List of deployable components found")

SYSTEM_PROMPT = """You are a Repository Architect. Your goal is to analyze the file structure of a repository and identify the distinct deployable components (services, apps, frontends).

## Logic for Detection
1. **Single Repo**: If you see configuration files only at the root (package.json, pom.xml, Dockerfile) and no distinct sub-projects, it is NOT a monorepo. Return `is_monorepo=False` and a single component at path ".".
2. **Monorepo**: If you see grouped subdirectories with their own configurations (e.g., `backend/package.json`, `frontend/package.json`, `services/auth/pom.xml`), it is a monorepo.
3. **Exclude**: Do NOT include shared libraries, utility packages, or configuration folders as deployable components unless they seem to be standalone services. Do NOT include `node_modules` or build artifacts.

## Markers
- Node.js: `package.json`
- Java: `pom.xml`, `build.gradle`
- Python: `requirements.txt`, `pyproject.toml`, `Dockerfile`
- Docker: `Dockerfile`

## Input
You will receive a list of files. Focus on the directory structure and marker files.
"""

async def monorepo_detector_agent(state: AgentState):
    """
    Detects if the repository is a monorepo and identifies components.
    Populates state['components'].
    """
    project_id = state.get("project_id", "")
    file_list = state.get("file_list", [])
    
    send_terminal_message(project_id, "🔍 Scanning repository structure for components...\n\r")
    
    # Pre-filter file list to relevant markers to save context window tokens
    relevant_markers = {"package.json", "pom.xml", "build.gradle", "requirements.txt", "pyproject.toml", "Dockerfile", "dockerfile", "go.mod"}
    
    # We want to see deep structure, but maybe filter out node_modules to avoid noise
    filtered_list = [
        f for f in file_list 
        if not any(stop in f for stop in ["node_modules/", "target/", "dist/", "build/", ".git/", "temp/", ".venv/", "venv/", ".idea/", ".vscode/"])
        and (f.split("/")[-1] in relevant_markers or f.count("/") <= 2) # Include markers OR top-level structure
    ]
    
    # If list is still huge, just take the top 2000 lines
    if len(filtered_list) > 2000:
        filtered_list = filtered_list[:2000]

    llm = ChatOpenAI(
        model="gpt-5-mini",
        api_key=settings.openai_key,
        temperature=0
    )
    llm_with_structure = llm.with_structured_output(MonorepoDetectionOutput)
    
    file_str = "\n".join(filtered_list)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Here is the filtered file list:\n\n{file_str}")
    ]
    
    response: MonorepoDetectionOutput = await llm_with_structure.ainvoke(messages)
    
    components_data = []
    
    if not response.is_monorepo and len(response.components) == 1:
        send_terminal_message(project_id, "ℹ️ Detected Single Repository structure.\n\r")
    else:
        send_terminal_message(project_id, f"📦 Detected Monorepo with {len(response.components)} components.\n\r")
        
    for comp in response.components:
        send_terminal_message(project_id, f"   - Found {comp.type} component: {comp.name} at {comp.path}\n\r")
        
        # Calculate file subset for this component
        # If path is ".", it gets everything.
        # If path is "backend", it gets "backend/..." (relative truncated or kept full?)
        # Let's keep full paths in file_list for now, but maybe the analysis agent needs to know the specific subset.
        
        comp_prefix = comp.path if comp.path != "." else ""
        if comp_prefix:
            # Filter files that start with this prefix
            comp_files = [f for f in file_list if f.startswith(comp_prefix + "/")]
        else:
            comp_files = file_list
            
        components_data.append({
            "name": comp.name,
            "path": comp.path,
            "type": comp.type,
            "file_list": comp_files,
            "analysis": None,
            "dockerfile_content": None,
            "image_url": None
        })
        
    return {
        "components": components_data,
        "current_step_index": 0 # Reset or use for loop iteration
    }
