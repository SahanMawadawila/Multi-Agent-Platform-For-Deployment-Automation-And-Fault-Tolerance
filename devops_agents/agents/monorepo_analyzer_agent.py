from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from config.settings import settings
from app.kafka_terminal_producer import send_terminal_message
from tools.git_tools import AsyncGitTools
from pydantic import BaseModel, Field
from typing import List, Dict


class ComponentAnalysis(BaseModel):
    name: str = Field(..., description="Name of the component (e.g., 'backend', 'frontend', 'auth-service')")
    path: str = Field(..., description="Path to the component root relative to repo root (e.g., 'frontend', 'services/backend')")
    type: str = Field(..., description="Project type: 'node', 'spring-boot', 'python', 'static', 'other'")
    role: str = Field("backend", description="Component role: 'frontend', 'backend', 'worker', 'api-gateway'")
    api_path_prefix: str = Field("/", description="Ingress path prefix: '/' for frontend, '/api' for backend, '/auth' for auth, etc.")
    networking_env_overrides: Dict[str, str] = Field(
        default_factory=dict,
        description="Env var overrides for inter-service communication. Key=env var name, Value=the path prefix value. E.g. {'REACT_APP_API_URL': '/api', 'NEXT_PUBLIC_BACKEND_URL': '/api'}"
    )


class MonorepoAnalysisOutput(BaseModel):
    components: List[ComponentAnalysis] = Field(..., description="Full analysis of each deployable component")


ENV_FILE_PATTERNS = [
    ".env", ".env.example", ".env.local", ".env.development",
    "docker-compose.yml", "docker-compose.yaml"
]


SYSTEM_PROMPT = """You are a Repository & Networking Architect analyzing a multi-component (monorepo) repository.

## Your Tasks

### 1. Identify Deployable Components
- Find each independently deployable service/app in the repository
- Each component must have its own configuration (package.json, pom.xml, Dockerfile, requirements.txt)
- Exclude: shared libraries, utility packages, config folders, node_modules, build artifacts

### 2. Detect Role of Each Component
- **frontend**: React, Next.js, Vue, Angular, static sites (serves UI to browsers)
- **backend**: Express, NestJS, Spring Boot, Django, FastAPI (API server)
- **worker**: Queue consumers, cron jobs, background processors
- **api-gateway**: API gateways, reverse proxies

### 3. Assign API Path Prefix (for Ingress path-based routing)
- Frontend components: always "/"
- Backend/API components: "/api" by default
- If multiple backends exist, use unique prefixes: "/api", "/auth", "/payments"

### 4. Detect Networking Env Overrides
Analyze env files to find variables referencing OTHER services:
- In frontend components: `REACT_APP_API_URL`, `NEXT_PUBLIC_API_URL`, `VITE_API_URL`, `API_BASE_URL`, `BACKEND_URL`
  → Override to the BACKEND component's api_path_prefix (e.g., "/api")
- In backend components referencing other backends: `AUTH_SERVICE_URL`, etc.
  → Override to that target component's api_path_prefix

**Important:**
- Only include env vars referencing OTHER components (not databases — those are handled separately)
- Override values should be the path prefix string (e.g., "/api"), NOT a full URL

## Markers for Component Detection
- Node.js: `package.json`
- Java: `pom.xml`, `build.gradle`
- Python: `requirements.txt`, `pyproject.toml`
- Docker: `Dockerfile`

## Input
You will receive:
1. Filtered file list showing directory structure and marker files
2. Contents of env files from the repository
"""


async def analyze_monorepo(file_list: list, project_id: str, local_path: str) -> list:
    """
    Full monorepo analysis: identifies components, detects roles, API path prefixes,
    and networking env overrides.
    
    Called ONLY when monorepo_detector returns True.
    
    Returns a list of component dicts:
    [{"name", "path", "type", "role", "api_path_prefix", "networking_env_overrides", "file_list"}]
    """
    send_terminal_message(project_id, "🧠 Analyzing monorepo components and networking...\n\r")
    
    # Pre-filter file list to relevant markers
    relevant_markers = {"package.json", "pom.xml", "build.gradle", "requirements.txt", 
                        "pyproject.toml", "Dockerfile", "dockerfile", "go.mod"}
    
    filtered_list = [
        f for f in file_list 
        if not any(stop in f for stop in ["node_modules/", "target/", "dist/", "build/", ".git/", 
                                           "temp/", ".venv/", "venv/", ".idea/", ".vscode/"])
        and (f.split("/")[-1] in relevant_markers or f.count("/") <= 2)
    ]
    
    if len(filtered_list) > 2000:
        filtered_list = filtered_list[:2000]
    
    # Read env files for networking analysis
    env_contents = {}
    for f in file_list:
        basename = f.split("/")[-1].lower()
        if basename in [p.lower() for p in ENV_FILE_PATTERNS]:
            try:
                content = await AsyncGitTools.read_file(local_path, f)
                if content and not content.startswith("Error") and len(content) < 5000:
                    env_contents[f] = content
            except Exception:
                pass
    
    env_section = ""
    if env_contents:
        send_terminal_message(project_id, f"📄 Reading {len(env_contents)} env/config file(s)...\n\r")
        for filepath, content in env_contents.items():
            env_section += f"\n--- {filepath} ---\n{content}\n"
    else:
        env_section = "\n(No env files found in repository)\n"
    
    llm = ChatOpenAI(
        model="gpt-5",
        api_key=settings.openai_key,
        temperature=0
    )
    llm_with_structure = llm.with_structured_output(MonorepoAnalysisOutput, method="function_calling")
    
    file_str = "\n".join(filtered_list)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Analyze this monorepo:\n\n## File Structure:\n{file_str}\n\n## Environment Files:\n{env_section}")
    ]
    
    response: MonorepoAnalysisOutput = await llm_with_structure.ainvoke(messages)
    
    # Build enriched component list
    components_data = []
    
    send_terminal_message(project_id, f"📦 Identified {len(response.components)} component(s):\n\r")
    for comp in response.components:
        override_info = f" | envs: {list(comp.networking_env_overrides.keys())}" if comp.networking_env_overrides else ""
        send_terminal_message(project_id, f"   🔗 {comp.name} ({comp.role}, {comp.type}) → {comp.path} | prefix={comp.api_path_prefix}{override_info}\n\r")
        
        # Calculate file subset for this component
        comp_prefix = comp.path if comp.path != "." else ""
        if comp_prefix:
            comp_files = [f for f in file_list if f.startswith(comp_prefix + "/")]
        else:
            comp_files = file_list
        
        components_data.append({
            "name": comp.name,
            "path": comp.path,
            "type": comp.type,
            "role": comp.role,
            "api_path_prefix": comp.api_path_prefix,
            "networking_env_overrides": comp.networking_env_overrides,
            "file_list": comp_files,
        })

    #print components_data
    print("networking env overrides", response.networking_env_overrides)
    
    send_terminal_message(project_id, "✅ Monorepo analysis complete.\n\r")
    return components_data
