from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from jinja2 import Environment, FileSystemLoader
from state import K8sResources, AppAnalysis

class k8sArchitectOutput(BaseModel):
    replicas: int = Field(..., description="Number of replicas for the deployment")
    cpu_limit: str = Field(..., description="CPU limit for each pod (e.g., '500m' for 0.5 CPU)")
    memory_limit: str = Field(..., description="Memory limit for each pod (e.g., '256Mi' for 256 MiB)")

class K8sArchitect:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4-turbo")
        self.env = Environment(loader=FileSystemLoader("templates/k8s"))

    def determine_resources(self, analysis: AppAnalysis) -> K8sResources:
        # The LLM decides the SIZE of the pod based on the framework
        structured_llm = self.llm.with_structured_output(K8sResources)
        prompt = f"Determine K8s resources for a {analysis.framework} app. Return reasonable defaults."
        return structured_llm.invoke(prompt)

    def generate_manifests(self, analysis: AppAnalysis, image_url: str):
        resources = self.determine_resources(analysis)
        template = self.env.get_template("deployment.j2")
        
        return template.render(
            app_name="my-agent-app",
            namespace="default",
            replicas=resources.replicas,
            image_url=image_url,
            port=analysis.port,
            memory_limit=resources.memory_limit,
            cpu_limit=resources.cpu_limit
        )