# agents/pipeline_agent.py
import boto3
import time
import base64
import requests
import os
from nacl import public, encoding
from botocore.exceptions import ClientError, EndpointConnectionError, ConnectionClosedError
from jinja2 import Environment, FileSystemLoader
from state import AgentState
from tools.git_tools import AsyncGitTools
from config.settings import settings

class PipelineAgent:
    def __init__(self):
        self.env = Environment(loader=FileSystemLoader("templates/github"))
        self.ecr_client = boto3.client(
            "ecr",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key,
            aws_secret_access_key=settings.aws_secret_key
        )

    # --- AWS ECR LOGIC ---
    def ensure_ecr_repo(self, repo_name: str):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ecr_client.describe_repositories(repositoryNames=[repo_name])
                print(f"✅ ECR Repository '{repo_name}' already exists.")
                return 
            except self.ecr_client.exceptions.RepositoryNotFoundException:
                print(f"⚠️ ECR Repository '{repo_name}' not found. Creating...")
                try:
                    self.ecr_client.create_repository(
                        repositoryName=repo_name,
                        imageScanningConfiguration={'scanOnPush': True},
                        encryptionConfiguration={'encryptionType': 'AES256'}
                    )
                    print(f"🚀 Created ECR Repository: {repo_name}")
                    return
                except Exception as e:
                    print(f"❌ Failed to create repo: {e}")
                    raise e
            except (EndpointConnectionError, ConnectionClosedError) as e:
                print(f"📡 AWS Connection failed. Retrying in 5s...")
                time.sleep(5)
                if attempt == max_retries - 1: raise e
            except ClientError as e:
                print(f"❌ AWS Error: {e}")
                raise e

    # --- GITHUB SECRETS AUTOMATION ---
    def set_github_secret(self, owner: str, repo: str, secret_name: str, secret_value: str):
        """
        Encrypts and uploads a secret to the GitHub Repository.
        """
        headers = {
            "Authorization": f"token {settings.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        base_url = f"https://api.github.com/repos/{owner}/{repo}"

        # 1. Get the Repo's Public Key
        key_url = f"{base_url}/actions/secrets/public-key"
        resp = requests.get(key_url, headers=headers)
        if resp.status_code != 200:
            print(f"❌ Failed to get GitHub public key: {resp.text}")
            return
        
        public_key_data = resp.json()
        key_id = public_key_data["key_id"]
        public_key = public_key_data["key"]

        # 2. Encrypt the Secret (LibSodium Sealed Box)
        public_key_bytes = base64.b64decode(public_key)
        sealed_box = public.SealedBox(public.PublicKey(public_key_bytes))
        encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
        encrypted_b64 = base64.b64encode(encrypted).decode("utf-8")

        # 3. Upload the Secret
        secret_url = f"{base_url}/actions/secrets/{secret_name}"
        data = {
            "encrypted_value": encrypted_b64,
            "key_id": key_id
        }
        put_resp = requests.put(secret_url, headers=headers, json=data)
        
        if put_resp.status_code in [201, 204]:
            print(f"🔐 Secret '{secret_name}' set successfully for {owner}/{repo}")
        else:
            print(f"❌ Failed to set secret '{secret_name}': {put_resp.text}")

    async def generate_and_push(self, state: AgentState):
        local_path = state["local_path"]
        ecr_repo_name = state["project_id"]
        repo_owner = state["repo_owner"]
        repo_name = state["repo_name"]

        print(f"🔍 Checking AWS ECR for Project ID: {ecr_repo_name}...")
        self.ensure_ecr_repo(ecr_repo_name)

        print(f"🔑 Injecting AWS Secrets into GitHub Repo {repo_owner}/{repo_name}...")
        try:
            self.set_github_secret(repo_owner, repo_name, "AWS_ACCESS_KEY_ID", settings.aws_access_key)
            self.set_github_secret(repo_owner, repo_name, "AWS_SECRET_ACCESS_KEY", settings.aws_secret_key)
        except Exception as e:
            print(f"⚠️ Warning: Could not set secrets automatically. Check token permissions. Error: {e}")

        workflow_content = f"""name: Build and Push to AWS ECR

on:
  push:
    branches: [ "main", "master" ]
  workflow_dispatch:

env:
  AWS_REGION: {settings.aws_region}
  ECR_REPOSITORY: {ecr_repo_name}

jobs:
  build-and-push:
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
          IMAGE_TAG: latest
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          echo "::set-output name=image::$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG"
"""
        
        print(f"⚙️ Generated AWS ECR Pipeline. Pushing to .github/workflows/ci.yml...")
        
        await AsyncGitTools.write_and_push(
            local_path, 
            ".github/workflows/ci.yml", 
            workflow_content, 
            "feat: Add automated AWS ECR pipeline"
        )
        
        return {"workflow_content": workflow_content}

# --- THIS WAS MISSING IN THE PREVIOUS FILE ---
async def pipeline_node(state: AgentState):
    agent = PipelineAgent()
    return await agent.generate_and_push(state)