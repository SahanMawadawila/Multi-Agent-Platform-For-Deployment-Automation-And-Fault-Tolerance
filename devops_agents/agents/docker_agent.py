from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from state import AgentState
from tools.git_tools import AsyncGitTools
from app.kafka_terminal_producer import send_terminal_message
from config.settings import settings

DOCKERFILE_PROMPT = """You are a Docker expert. Generate a production-ready Dockerfile based on the project analysis provided.

## Requirements:
1. Use multi-stage builds to minimize image size
2. Use Alpine-based images when possible
3. Run as non-root user for security
4. Use appropriate base image version (not 'latest')
5. Copy only necessary files
6. Set proper working directory
7. Expose the correct port
8. Use proper CMD format

## Project Analysis:
- Project Type: {project_type}
- Framework: {framework}
- Runtime Version: {version}
- Package Manager: {package_manager}
- Build Command: {build_command}
- Run Command: {run_command}
- Port: {port}
- Has Lockfile: {has_lockfile}
- Environment Variables: {env_variables}

## Response Format:
Return ONLY the Dockerfile content, no explanations or markdown code blocks.
Start directly with # syntax=docker/dockerfile:1 or FROM statement.
"""

async def docker_writing_agent(state: AgentState):
    """AI-powered Docker agent that generates production Dockerfiles."""
    
    analysis = state["analyzed_repository_details"]
    local_path = state["local_path"]
    project_id = state.get("project_id", "")
    
    send_terminal_message(project_id, "🐳 Generating Dockerfile...\n\r")
    
    # Build LLM
    llm = ChatOpenAI(
        model="gpt-5.1-mini",
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
    
    send_terminal_message(project_id, "📝 Dockerfile generated. Pushing to repository...\n\r")
    
    # Push to repository
    await AsyncGitTools.write_and_push(
        local_path,
        "Dockerfile",
        dockerfile_content,
        "feat: Add Dockerfile via AI Agent"
    )
    
    send_terminal_message(project_id, "✅ Dockerfile pushed successfully!\n\r")
    
    return {"dockerfile_content": dockerfile_content}