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
            print(f"❌ Failed to get public key for {owner}/{repo}: {key_resp.status_code} - {key_resp.text}")
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
        
        if put_resp.status_code in [201, 204]:
            print(f"✅ Secret {secret_name} set successfully for {owner}/{repo}")
            return True
        else:
            print(f"❌ Failed to set secret {secret_name}: {put_resp.status_code} - {put_resp.text}")
            return False
    except Exception as e:
        print(f"❌ Exception setting secret {secret_name}: {e}")
        return False

# ============== WORKFLOW TEMPLATE ==============
def generate_workflow_content(aws_region: str, ecr_repo_name: str) -> str:
    """Generate GitHub Actions workflow for AWS ECR deployment."""
    return f"""name: Build and Push to AWS ECR

on:
  push:
    branches: [ "main", "master" ]
  workflow_dispatch:

env:
  AWS_REGION: {aws_region}
  ECR_REPOSITORY: {ecr_repo_name}

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{{{ secrets.AWS_ACCESS_KEY_ID }}}}
          aws-secret-access-key: ${{{{ secrets.AWS_SECRET_ACCESS_KEY }}}}
          aws-region: ${{{{ env.AWS_REGION }}}}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build, tag, and push image to Amazon ECR
        id: build-image
        env:
          ECR_REGISTRY: ${{{{ steps.login-ecr.outputs.registry }}}}
          IMAGE_TAG: ${{{{ github.sha }}}}
        run: |
          echo "Building Docker image..."
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG -t $ECR_REGISTRY/$ECR_REPOSITORY:latest .
          echo "Pushing to ECR..."
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest
          echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_OUTPUT
"""

# ============== MAIN AGENT ==============
async def pipeline_writing_agent(state: AgentState):
    """Generates CI/CD pipeline for AWS ECR deployment."""
    
    project_id = state.get("project_id", "")
    local_path = state["local_path"]
    repo_owner = state["repo_owner"]
    repo_name = state["repo_name"]
    ecr_repo_name = project_id
    
    send_terminal_message(project_id, "🚀 Starting CI/CD pipeline generation...\n\r")
    
    # Debug: Print configuration
    print(f"📋 Pipeline Config:")
    print(f"   - AWS Region: {settings.aws_region}")
    print(f"   - ECR Repo: {ecr_repo_name}")
    print(f"   - GitHub Repo: {repo_owner}/{repo_name}")
    print(f"   - AWS Key: {settings.aws_access_key[:10]}..." if settings.aws_access_key else "   - AWS Key: NOT SET!")
    
    # Validate AWS credentials
    if not settings.aws_access_key or not settings.aws_secret_key:
        send_terminal_message(project_id, "❌ AWS credentials not configured!\n\r")
        print("❌ Missing AWS_ACCESS_KEY or AWS_SECRET_KEY in .env")
        return {"error": "Missing AWS credentials"}
    
    try:
        # Setup ECR
        ecr_client = boto3.client(
            "ecr",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key,
            aws_secret_access_key=settings.aws_secret_key
        )
        
        send_terminal_message(project_id, f"☁️ Setting up AWS ECR repository in {settings.aws_region}...\n\r")
        ecr_success = ensure_ecr_repo(ecr_client, ecr_repo_name)
        if ecr_success:
            send_terminal_message(project_id, "✅ ECR repository ready\n\r")
        else:
            send_terminal_message(project_id, "⚠️ ECR setup may have issues\n\r")
        
        # Set GitHub secrets
        send_terminal_message(project_id, "🔐 Configuring deployment secrets...\n\r")
        key_set = set_github_secret(repo_owner, repo_name, "AWS_ACCESS_KEY_ID", settings.aws_access_key)
        secret_set = set_github_secret(repo_owner, repo_name, "AWS_SECRET_ACCESS_KEY", settings.aws_secret_key)
        
        if key_set and secret_set:
            send_terminal_message(project_id, "✅ GitHub secrets configured\n\r")
        else:
            send_terminal_message(project_id, f"⚠️ GitHub secrets setup: KEY={key_set}, SECRET={secret_set}\n\r")
            print(f"⚠️ Failed to set GitHub secrets - check GITHUB_TOKEN has admin:repo_hook scope")
        
        # Generate and push workflow
        send_terminal_message(project_id, "📝 Generating GitHub Actions workflow...\n\r")
        workflow_content = generate_workflow_content(settings.aws_region, ecr_repo_name)
        
        await AsyncGitTools.write_and_push(
            local_path, 
            ".github/workflows/ci.yml", 
            workflow_content, 
            "feat: Add automated AWS ECR pipeline"
        )
        
        send_terminal_message(project_id, "✅ CI/CD pipeline configured successfully!\n\r")
        
        return {"workflow_content": workflow_content}
        
    except Exception as e:
        error_msg = f"Pipeline generation failed: {str(e)}"
        print(f"❌ {error_msg}")
        send_terminal_message(project_id, f"❌ {error_msg}\n\r")
        return {"error": error_msg}