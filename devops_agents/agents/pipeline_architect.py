# agents/pipeline_architect.py
from jinja2 import Environment, FileSystemLoader
from state import RepoFacts

class PipelineArchitect:
    def __init__(self):
        self.env = Environment(loader=FileSystemLoader("templates/github"))

    def create_ecr_pipeline(self, facts: RepoFacts, repo_name: str) -> str:
        """
        Generates a GitHub Action to:
        1. Checkout
        2. Config AWS Credentials
        3. Login to ECR
        4. Build & Push Docker Image
        """
        template = self.env.get_template("aws_ecr_workflow.j2")
        
        return template.render(
            branch="main", # Could be dynamic
            aws_region="us-east-1",
            ecr_repository=repo_name,
            build_context="."
        )