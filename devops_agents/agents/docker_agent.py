from jinja2 import Environment, FileSystemLoader
from state import AgentState
from tools.git_tools import AsyncGitTools
import json
from app.kafka_terminal_producer import send_terminal_message

class DockerAgent:
    def __init__(self):
        self.env = Environment(loader=FileSystemLoader("templates/docker"))

    async def generate_and_push(self, state: AgentState):
        analysis = state["analyzed_repository_details"]
        local_path = state["local_path"]

        # Parse run command to JSON array for CMD if needed, or keep string
        # For simplicity in this robust template, we use shell form CMD string in template
        
        # Select Template
        template = self.env.get_template("node_universal.j2")
        
        # Render
        dockerfile_content = template.render(
            version=analysis.version,
            package_manager=analysis.package_manager,
            build_command=analysis.build_command,
            env_variables=analysis.env_variables,
            port=analysis.port,
            run_command=f"[{', '.join(json.dumps(analysis.run_command.split(' ')))}]" if " " in analysis.run_command else f'"{analysis.run_command}"',
            framework=analysis.framework
        )

        # Write and Push
        print("🐳 Generated Dockerfile. Pushing...")
        send_terminal_message(state["project_id"], "🐳 Generated Dockerfile. Pushing...\n\r")
        await AsyncGitTools.write_and_push(
            local_path, 
            "Dockerfile", 
            dockerfile_content, 
            "feat: Add robust Dockerfile via Agent"
        )
        
        return {"dockerfile_content": dockerfile_content}

# Standalone function for the graph
async def docker_node(state: AgentState):
    agent = DockerAgent()
    return await agent.generate_and_push(state)