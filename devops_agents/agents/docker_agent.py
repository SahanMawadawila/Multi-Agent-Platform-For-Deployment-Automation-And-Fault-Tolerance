from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from state import AgentState
from tools.git_tools import AsyncGitTools
from app.kafka_terminal_producer import send_terminal_message
from config.settings import settings

DOCKERFILE_PROMPT = """You are a Docker expert. Generate a production-ready Dockerfile based on the project analysis.

## Build Strategy:
- If needs_build_step is FALSE: Use a SINGLE-STAGE build. Just install dependencies and copy source files.
- If needs_build_step is TRUE: Use MULTI-STAGE build (builder + runner stages).

## Requirements:
1. Use Alpine-based images when possible
2. Use specific base image version (not 'latest')
3. If you need nodejs image, use node:{version}-alpine image format, with no any tags.
4. Expose the correct port
5. Use proper CMD format (JSON array)
6. Assume the Dockerfile is placed in the project root. COPY commands should enable relative paths from the project root (e.g. "COPY package.json ."). Do NOT assume a monorepo structure where you need to copy from parent folders.

## Additional Instructions:
- If a node project has postinstall, makesure to copy everything in the project directory before running npm install.
- if executable file like mvnw or gradlew is present, add chmod +x command for it in the Dockerfile before running it.
- for pure react apps, build it and serve with a lightweight web server like nginx.
- For Spring Boot apps, use a multi-determine weather to build as war or jar and use appropriate base images and commands.

## Project Analysis:
- Project Type: {project_type}
- Framework: {framework}
- Runtime Version: {version}
- Package Manager: {package_manager}
- Build Command: {build_command}
- Run Command: {run_command}
- Port: {port}
- Has Lockfile: {has_lockfile}
- Needs Build Step: {needs_build_step}
- Environment Variables: {env_variables}

## Response:
Return ONLY the Dockerfile content. No markdown, no explanations.
"""

async def docker_writing_agent(state: AgentState):
    """AI-powered Docker agent that generates production Dockerfiles."""
    
    analysis = state["analyzed_repository_details"]
    local_path = state["local_path"]
    project_id = state.get("project_id", "")
    component_name = state.get("component_name")
    
    send_terminal_message(project_id, "🐳 Generating Dockerfile...\n\r", component_name)
    
    # Build LLM
    llm = ChatOpenAI(
        model="gpt-5-mini",
        api_key=settings.openai_key,
        temperature=0
    )
    
    # Format prompt with analysis data
    prompt = DOCKERFILE_PROMPT.format(
        project_type=analysis.project_type,
        framework=analysis.framework or "N/A",
        version=analysis.version,
        package_manager=analysis.package_manager,
        build_command=analysis.build_command or "N/A",
        run_command=analysis.run_command,
        port=analysis.port,
        has_lockfile=analysis.has_lockfile,
        needs_build_step=getattr(analysis, 'needs_build_step', False),
        env_variables=", ".join(analysis.env_variables) if analysis.env_variables else "None"
    )
    
    # Generate Dockerfile
    messages = [
        SystemMessage(content="You are a Docker expert. Generate only Dockerfile content, no explanations."),
        HumanMessage(content=prompt)
    ]
    
    response = await llm.ainvoke(messages)
    dockerfile_content = response.content.strip()
    
    # Clean up any markdown code blocks if present
    if dockerfile_content.startswith("```"):
        lines = dockerfile_content.split("\n")
        dockerfile_content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
    
    send_terminal_message(project_id, "📝 Dockerfile generated. Pushing to repository...\n\r", component_name)

    # Push to repository
    await AsyncGitTools.write_and_push(
        local_path,
        'Dockerfile',
        dockerfile_content,
        "feat: Add Dockerfile via AI Agent"
    )
    
    send_terminal_message(project_id, "✅ Dockerfile pushed successfully!\n\r", component_name)
    
    return {"dockerfile_content": dockerfile_content}