import boto3
import time
import base64
import requests
from nacl import public
from botocore.exceptions import ClientError, EndpointConnectionError, ConnectionClosedError
from state import AgentState
from tools.git_tools import AsyncGitTools
from config.settings import settings
from app.kafka_terminal_producer import send_terminal_message

# ============== AWS ECR HELPER ==============
def ensure_ecr_repo(ecr_client, repo_name: str) -> bool:
    """Ensure ECR repository exists, create if not. Returns True on success."""
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            ecr_client.describe_repositories(repositoryNames=[repo_name])
            return True
        except ecr_client.exceptions.RepositoryNotFoundException:
            try:
                ecr_client.create_repository(
                    repositoryName=repo_name,
                    imageScanningConfiguration={'scanOnPush': True},
                    encryptionConfiguration={'encryptionType': 'AES256'}
                )
                return True
            except Exception:
                return False
        except (EndpointConnectionError, ConnectionClosedError):
            time.sleep(5)
            if attempt == max_retries - 1:
                return False
        except ClientError:
            return False
    return False

# ============== GITHUB SECRETS HELPER ==============
def set_github_secret(owner: str, repo: str, secret_name: str, secret_value: str) -> bool:
    """Encrypt and upload a secret to GitHub Repository. Returns True on success."""
    headers = {
        "Authorization": f"token {settings.github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    base_url = f"https://api.github.com/repos/{owner}/{repo}"

    try:
        # Get the repo's public key
        key_resp = requests.get(f"{base_url}/actions/secrets/public-key", headers=headers)
        if key_resp.status_code != 200:
            return False
        
        public_key_data = key_resp.json()
        key_id = public_key_data["key_id"]
        public_key = public_key_data["key"]

        # Encrypt the secret (LibSodium Sealed Box)
        public_key_bytes = base64.b64decode(public_key)
        sealed_box = public.SealedBox(public.PublicKey(public_key_bytes))
        encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
        encrypted_b64 = base64.b64encode(encrypted).decode("utf-8")

        # Upload the secret
        secret_url = f"{base_url}/actions/secrets/{secret_name}"
        put_resp = requests.put(secret_url, headers=headers, json={
            "encrypted_value": encrypted_b64,
            "key_id": key_id
        })
        
        return put_resp.status_code in [201, 204]
    except Exception:
        return False

# ============== WORKFLOW TEMPLATE ==============
def generate_workflow_content(aws_region: str, ecr_repo: str, version: str, branch_name: str = None, component_path: str = None) -> str:
    """Generate GitHub Actions workflow for building and pushing a Docker image."""
    branches = f'[ "{branch_name}" ]' if branch_name else '[ "main", "master" ]'
    
    # For monorepo: build context is the component folder, Dockerfile is inside it
    if component_path:
        build_context = f"./{component_path}"
        dockerfile_path = f"./{component_path}/Dockerfile"
    else:
        build_context = "."
        dockerfile_path = "./Dockerfile"
    
    return f"""name: Build and Push
    
on:
  push:
    branches: {branches}
  workflow_dispatch:

env:
  AWS_REGION: {aws_region}
  ECR_REPOSITORY: {ecr_repo}

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read

    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{{{ secrets.AWS_ACCESS_KEY_ID }}}}
          aws-secret-access-key: ${{{{ secrets.AWS_SECRET_ACCESS_KEY }}}}
          aws-region: ${{{{ env.AWS_REGION }}}}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1

      - name: Build, tag, and push image to Amazon ECR
        id: build-image
        env:
          ECR_REGISTRY: ${{{{ steps.login-ecr.outputs.registry }}}}
          IMAGE_TAG: "{version}"
        run: |
          docker build -f {dockerfile_path} -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG {build_context}
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
"""

# ============== MAIN AGENT ==============
async def pipeline_writing_agent(state: AgentState):
    """Generates CI/CD pipeline for AWS ECR deployment (single component per invocation)."""
    
    project_id = state.get("project_id", "")
    build_version = state.get("build_version", "latest")
    local_path = state["local_path"]
    repo_owner = state["repo_owner"]
    repo_name = state["repo_name"]
    component_name = state.get("component_name")  # None for single project
    branch_name = state.get("branch_name")  # None for single project
    
    send_terminal_message(project_id, "🚀 Starting CI/CD pipeline generation...\n\r", component_name)
    
    # Setup ECR
    ecr_client = boto3.client(
        "ecr",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key,
        aws_secret_access_key=settings.aws_secret_key
    )
    
    # ECR naming: project_id for single project, project_id-{name} for multi-project
    if component_name:
        ecr_repo_name = f"{project_id}-{component_name}"
    else:
        ecr_repo_name = project_id
    
    send_terminal_message(project_id, f"☁️ Setting up AWS ECR repository: {ecr_repo_name}...\n\r", component_name)
    ensure_ecr_repo(ecr_client, ecr_repo_name)
    
    try:
        registry_uri = f"{settings.aws_account_id}.dkr.ecr.{settings.aws_region}.amazonaws.com"
        image_url = f"{registry_uri}/{ecr_repo_name}:{build_version}"
    except Exception:
        image_url = "Error-Resolving-Image-URL"

    # Set GitHub secrets
    send_terminal_message(project_id, "🔐 Configuring deployment secrets...\n\r", component_name)
    set_github_secret(repo_owner, repo_name, "AWS_ACCESS_KEY_ID", settings.aws_access_key)
    set_github_secret(repo_owner, repo_name, "AWS_SECRET_ACCESS_KEY", settings.aws_secret_key)
    
    # Generate and push workflow
    send_terminal_message(project_id, f"📝 Generating GitHub Actions workflow (version={build_version})...\n\r", component_name)
    component_path = state.get("component_path")  # None for single project
    workflow_content = generate_workflow_content(settings.aws_region, ecr_repo_name, build_version, branch_name, component_path)


    await AsyncGitTools.write_and_push(
        local_path, 
        ".github/workflows/ci.yml", 
        workflow_content, 
        f"feat: Update pipeline for version {build_version}"
    )
    
    send_terminal_message(project_id, "✅ CI/CD pipeline configured successfully!\n\r", component_name)
    
    return {
        "workflow_content": workflow_content,
        "image_url": image_url,
    }
