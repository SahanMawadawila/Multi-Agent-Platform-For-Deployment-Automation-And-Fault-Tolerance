# agents/docker_factory.py
from jinja2 import Environment, FileSystemLoader
from state import RepoFacts

class DockerFactory:
    def __init__(self):
        # Point to the templates directory
        self.env = Environment(loader=FileSystemLoader("templates/docker"))

    def generate_dockerfile(self, facts: RepoFacts) -> str:
        """
        Selects the correct template based on language and fills it.
        We do NOT use an LLM here for generation to avoid syntax errors.
        We use the LLM's *facts* to populate a rigid Jinja2 template.
        """
        
        # 1. Strategy Selection Logic
        if facts.language.lower() in ["node", "javascript", "typescript"]:
            template = self.env.get_template("node_multistage.j2")
            
            # Determine if 'npm run build' is needed
            # (In a real app, we'd check the scripts section of package.json from facts)
            has_build = True 
            
            return template.render(
                version=facts.version or "18", # Fallback if analysis failed
                package_manager=facts.build_tool,
                has_build_script=has_build,
                env_vars=facts.env_vars,
                port=facts.detected_ports[0] if facts.detected_ports else 8080
            )
            
        elif facts.language.lower() == "java":
            # Example of how we handle the Java branch
            template = self.env.get_template("java_maven_multistage.j2")
            return template.render(
                version=facts.version or "17",
                port=facts.detected_ports[0] if facts.detected_ports else 8080
            )
            
        else:
            raise ValueError(f"Language {facts.language} not supported yet.")