from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from config.settings import settings
from app.kafka_terminal_producer import send_terminal_message
from pydantic import BaseModel, Field


class MonorepoDetectionOutput(BaseModel):
    is_monorepo: bool = Field(..., description="True if the repository contains multiple deployable components, False if it's a single project")


SYSTEM_PROMPT = """You are a Repository Architect. Analyze the file structure and determine if this is a monorepo (multiple deployable services/apps) or a single project.

## Single Project indicators:
- Configuration files only at root (package.json, pom.xml)
- No distinct sub-project directories with their own configs
- Standard project layout (src/, lib/, public/)

## Monorepo indicators:
- Multiple subdirectories each with their own package.json, pom.xml, or Dockerfile
- Directory names like: frontend/, backend/, services/, apps/, packages/
- Example: `frontend/package.json` + `backend/package.json`

## NOT a monorepo:
- A monorepo tool workspace (like npm workspaces or Lerna) with shared libraries is still a single deployable unit unless subdirectories are independently deployable services
- node_modules, build artifacts, config folders do not count

Return is_monorepo=True ONLY if there are clearly distinct, independently deployable components.
"""


async def detect_monorepo(file_list: list, project_id: str) -> bool:
    """
    Simple monorepo detector. Returns True if the repo has multiple deployable components, False otherwise.
    """
    send_terminal_message(project_id, "🔍 Checking if repository is a monorepo...\n\r")
    
    # Pre-filter file list to relevant markers
    relevant_markers = {"package.json", "pom.xml", "build.gradle", "requirements.txt", "pyproject.toml", "Dockerfile", "dockerfile", "go.mod"}
    
    filtered_list = [
        f for f in file_list 
        if not any(stop in f for stop in ["node_modules/", "target/", "dist/", "build/", ".git/", "temp/", ".venv/", "venv/", ".idea/", ".vscode/"])
        and (f.split("/")[-1] in relevant_markers or f.count("/") <= 2)
    ]
    
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
        HumanMessage(content=f"Is this a monorepo?\n\n{file_str}")
    ]
    
    response: MonorepoDetectionOutput = await llm_with_structure.ainvoke(messages)
    
    if response.is_monorepo:
        send_terminal_message(project_id, "📦 Monorepo detected! Multiple components found.\n\r")
    else:
        send_terminal_message(project_id, "📦 Single project detected.\n\r")
    
    return response.is_monorepo
