import boto3
import time
import base64
import requests
import re
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
def generate_standard_workflow_content(aws_region: str, ecr_repo: str, version: str) -> str:
    """Generate GitHub Actions workflow for a standard Single Repo project."""
    return f"""name: Build and Push
    
on:
  push:
    branches: [ "main", "master" ]
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
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
"""

def generate_monorepo_workflow_content(aws_region: str, components: list, version: str) -> str:
    """Generate GitHub Actions workflow for multiple components (Monorepo)."""
    
    jobs_yaml = ""
    
    for comp in components:
        comp_name = comp["name"]
        # Sanitize name: Replace non-alphanumeric chars with '-', remove duplicate '-', strip leading/trailing '-'
        clean_comp_name = re.sub(r'[^a-zA-Z0-9]', '-', comp_name)
        clean_comp_name = re.sub(r'-+', '-', clean_comp_name).strip('-').lower()
        
        # Fallback if name becomes empty (e.g. if name was ".")
        if not clean_comp_name:
            clean_comp_name = "app"
            
        job_id = f"build-{clean_comp_name}"
        
        # Check deployment path context. 
        # Standard: docker build -f path/Dockerfile .
        dockerfile_path = "Dockerfile"
        if comp["path"] != ".":
            dockerfile_path = f"{comp['path']}/Dockerfile"
            
        ecr_repo = comp["ecr_repo"]
        
        jobs_yaml += f"""
  {job_id}:
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
          ECR_REPOSITORY: {ecr_repo}
          IMAGE_TAG: "{version}"
        run: |
          # If component is in a subdirectory, use it as build context to find local package.json
          # But we still use the Dockerfile from the root-relative path if that's where it is?
          # Actually, usually 'docker build path/to/component' works if Dockerfile is inside.
          
          # Fix for monorepo: Change directory to component path for build if it's not root
          # This ensures 'COPY package.json .' picks up the component's file, not root's.
          
          BUILD_CONTEXT="."
          DOCKER_FILE="{dockerfile_path}"
          
          if [ "{comp['path']}" != "." ]; then
             echo "Using component directory as build context: {comp['path']}"
             BUILD_CONTEXT="{comp['path']}"
             # If we moved context, Dockerfile is relative to that context? 
             # No, -f is relative to where we run 'docker build'.
             DOCKER_FILE="{dockerfile_path}"
          fi
          
          docker build -f $DOCKER_FILE -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $BUILD_CONTEXT
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
"""

    return f"""name: Build and Push (Monorepo)

on:
  push:
    branches: [ "main", "master" ]
  workflow_dispatch:

env:
  AWS_REGION: {aws_region}

jobs:{{jobs_yaml}}
"""

# ============== MAIN AGENT ==============
async def pipeline_writing_agent(state: AgentState):
    """Generates CI/CD pipeline for AWS ECR deployment."""
    
    project_id = state.get("project_id", "")
    build_version = state.get("build_version", "latest")
    local_path = state["local_path"]
    repo_owner = state["repo_owner"]
    repo_name = state["repo_name"]
    components = state.get("components", [])
    
    send_terminal_message(project_id, "🚀 Starting CI/CD pipeline generation...\n\r")
    
    # Setup ECR
    ecr_client = boto3.client(
        "ecr",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key,
        aws_secret_access_key=settings.aws_secret_key
    )
    
    # If no components found (legacy fallback), create one from state
    if not components:
        send_terminal_message(project_id, "⚠️ No components detected in state, using legacy single-repo mode.\n\r")
        components = [{
            "name": "app",
            "path": ".",
            "ecr_repo": project_id
        }]

    send_terminal_message(project_id, "☁️ Setting up AWS ECR repositories...\n\r")
    
    final_components = []
    
    for comp in components:
        # Naming convention:
        # Single Repo (path=".") -> project_id
        # Multi Repo -> project_id-{name} (cleaned)
        
        if len(components) == 1 and comp["path"] == ".":
            comp_ecr_name = project_id
        else:
            clean_name = comp["name"].replace("/", "-").replace(" ", "-").lower()
            comp_ecr_name = f"{project_id}-{clean_name}"
            
        send_terminal_message(project_id, f"   - Ensuring ECR repo: {comp_ecr_name}\n\r")
        ensure_ecr_repo(ecr_client, comp_ecr_name)
        
        try:
            registry_uri = f"{settings.aws_account_id}.dkr.ecr.{settings.aws_region}.amazonaws.com"
            image_url = f"{registry_uri}/{comp_ecr_name}:{build_version}"
        except Exception:
            image_url = "Error-Resolving-Image-URL"
        
        # Copy comp to dict and add extra fields used for template
        comp_data = comp.copy()
        comp_data["ecr_repo"] = comp_ecr_name
        comp_data["image_url"] = image_url
        final_components.append(comp_data)

    # Set GitHub secrets
    send_terminal_message(project_id, "🔐 Configuring deployment secrets...\n\r")
    set_github_secret(repo_owner, repo_name, "AWS_ACCESS_KEY_ID", settings.aws_access_key)
    set_github_secret(repo_owner, repo_name, "AWS_SECRET_ACCESS_KEY", settings.aws_secret_key)
    
    # Accept both "." and "./" as root path indicators
    is_standard_repo = len(final_components) == 1 and final_components[0]["path"] in [".", "./"]
    
    # Generate and push workflow
    send_terminal_message(project_id, f"📝 Generating GitHub Actions workflow (version={build_version})...\n\r")
    
    # Check if single repo or monorepo to choose template
    is_standard_repo = len(final_components) == 1 and final_components[0]["path"] == "."
    
    if is_standard_repo:
        workflow_content = generate_standard_workflow_content(settings.aws_region, final_components[0]["ecr_repo"], build_version)
    else:
        workflow_content = generate_monorepo_workflow_content(settings.aws_region, final_components, build_version)
    
    await AsyncGitTools.write_and_push(
        local_path, 
        ".github/workflows/ci.yml", 
        workflow_content, 
        f"feat: Update pipeline for version {build_version}"
    )
    
    send_terminal_message(project_id, "✅ CI/CD pipeline configured successfully!\n\r")
    
    # Return updated components list to state so K8s agent can use image_urls
    result = {
        "workflow_content": workflow_content,
        "components": final_components 
    }
    
    # Legacy backward compatibility for single repo agents that might check image_url at root state
    if len(final_components) == 1:
        result["image_url"] = final_components[0]["image_url"]
        
    return result
