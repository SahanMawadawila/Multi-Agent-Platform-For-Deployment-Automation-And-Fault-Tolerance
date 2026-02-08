import os
import shutil
import tempfile
import asyncio
from github import Github, Auth
from jinja2 import Environment, FileSystemLoader
from config.settings import settings
from app.kafka_terminal_producer import send_terminal_message
from tools.git_tools import AsyncGitTools
import subprocess
import boto3
import base64

async def k8s_architect_agent(state):
    """
    K8s Architect Agent:
    1. Reads parsed repo details from state.
    2. Creates a GitOps repo (if not exists).
    3. Generates K8s manifests (Deployment, Service, Ingress) from templates.
    4. Pushes manifests to the GitOps repo.
    5. Generates and pushes/applies ArgoCD Application manifest.
    """
    project_id = state.get("project_id", "")
    analysis = state.get("analyzed_repository_details")
    
    if not analysis:
        send_terminal_message(project_id, "❌ No repository analysis found. Skipping K8s Architect.\n\r")
        return {"build_status": "k8s_failed_no_analysis"}
        
    if not state.get("image_url"):
        send_terminal_message(project_id, "❌ No image URL found. Pipeline agent failed to provide image.\n\r")
        return {"build_status": "k8s_failed_no_image"}

    send_terminal_message(project_id, "👷 Starting K8s deployment...\n\r")

    # 1. Prepare Data
    app_name = f"app-{project_id}"
    namespace = project_id # Use project_id as namespace
    
    # Defaults
    data = {
        "app_name": app_name,
        "namespace": namespace,
        "replicas": 1,
        "image_url": state.get("image_url"), # Must be present
        "port": analysis.port,
        "memory_limit": getattr(analysis, "memory_limit", "256Mi"),
        "cpu_limit": getattr(analysis, "cpu_limit", "200m"),
        "health_check_path": getattr(analysis, "health_check_path", "/"),
        "image_pull_secret": "regcred"
    }

    # 1.5 Create Image Pull Secret (Kubernetes)
    try:
        send_terminal_message(project_id, "🔐 Configuring K8s Image Pull Secret for ECR...\n\r")
        
        # Get ECR Login Password
        ecr = boto3.client(
            "ecr", 
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key,
            aws_secret_access_key=settings.aws_secret_key
        )
        token = ecr.get_authorization_token()
        username, password = base64.b64decode(token['authorizationData'][0]['authorizationToken']).decode().split(':')
        server = token['authorizationData'][0]['proxyEndpoint']
        
        # Create Namespace first if not exists
        subprocess.run(["kubectl", "create", "namespace", namespace], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Create Secret (Delete if exists to update)
        # regcred is expired after 12 hours
        subprocess.run(["kubectl", "delete", "secret", "regcred", "-n", namespace], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Create new secret
        cmd = [
            "kubectl", "create", "secret", "docker-registry", "regcred",
            f"--docker-server={server}",
            f"--docker-username={username}",
            f"--docker-password={password}",
            f"--namespace={namespace}"
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
        send_terminal_message(project_id, "✅ Image Pull Secret 'regcred' created.\n\r")
        
    except Exception as e:
         send_terminal_message(project_id, f"⚠️ Failed to create K8s secret: {str(e)}\n\r")

    # 2. GitHub Setup (Create GitOps Repo)
    gitops_repo_name = f"gitops-{project_id}"
    gitops_repo_url = ""
    
    try:
        # Authenticate with GitHub
        auth = Auth.Token(settings.github_token)
        g = Github(auth=auth)
        
        org = g.get_organization(settings.github_org)

        # Create or Get Repo
        try:
            repo = org.get_repo(gitops_repo_name)
            send_terminal_message(project_id, f"✅ Found existing GitOps repo: {gitops_repo_name}\n\r")
        except Exception:
            send_terminal_message(project_id, f"✨ Creating new GitOps repo: {gitops_repo_name}\n\r")
            repo = org.create_repo(gitops_repo_name, private=True, auto_init=True)
        
        gitops_repo_url = repo.clone_url
        data["gitops_repo_url"] = gitops_repo_url
        
        # 2.5 Create ArgoCD Repo Secret (for Private Repos)
        send_terminal_message(project_id, "🔐 Configuring ArgoCD with GitHub credentials...\n\r")
        
        # Create Secret for ArgoCD to access private repo
        # Label: argocd.argoproj.io/secret-type=repository
        secret_name = f"repo-{project_id}"
        
        # Delete if exists
        subprocess.run(["kubectl", "delete", "secret", secret_name, "-n", "argocd"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        cmd_secret = [
            "kubectl", "create", "secret", "generic", secret_name,
            "-n", "argocd",
            f"--from-literal=type=git",
            f"--from-literal=url={gitops_repo_url}",
            f"--from-literal=password={settings.github_token}",
            f"--from-literal=username={settings.github_org or 'git'}"
        ]
        subprocess.run(cmd_secret, check=True, stdout=subprocess.DEVNULL)
        
        # Label the secret so ArgoCD picks it up
        subprocess.run(["kubectl", "label", "secret", secret_name, "-n", "argocd", "argocd.argoproj.io/secret-type=repository"], check=True, stdout=subprocess.DEVNULL)
        
        send_terminal_message(project_id, "✅ ArgoCD Repository Secret created.\n\r")

    except Exception as e:
        send_terminal_message(project_id, f"❌ GitHub Operation Failed: {str(e)}\n\r")
        return {"build_status": "k8s_github_failed"}

    # 3. Clone to Temp Dir
    temp_dir = os.path.join(os.getcwd(), "temp", f"gitops_{project_id}")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    
    send_terminal_message(project_id, f"📥 Cloning GitOps repo to {temp_dir}...\n\r")
    await AsyncGitTools.clone_repository(gitops_repo_url, temp_dir)

    # 4. Generate Manifests
    templates_dir = os.path.join(os.getcwd(), "templates", "k8s")
    env = Environment(loader=FileSystemLoader(templates_dir))
    
    manifests_path = os.path.join(temp_dir, "app")
    os.makedirs(manifests_path, exist_ok=True)
    
    files_to_generate = ["deployment.j2", "service.j2", "ingress.j2"]
    
    for template_file in files_to_generate:
        template = env.get_template(template_file)
        content = template.render(data)
        
        output_filename = template_file.replace(".j2", ".yaml")
        output_path = os.path.join(manifests_path, output_filename)
        
        with open(output_path, "w") as f:
            f.write(content)
        
        send_terminal_message(project_id, f"📄 Generated {output_filename}\n\r")

    # 5. Push to GitOps Repo
    send_terminal_message(project_id, "🚀 Pushing manifests to GitOps repo...\n\r")
    # We use bulk_push to ensure ALL generated files (deployment, service, ingress) are committed
    await AsyncGitTools.bulk_push(temp_dir, "Update K8s manifests")

    # 6. Apply ArgoCD Application
    argocd_template = env.get_template("argocd-application.j2")
    argocd_content = argocd_template.render(data)
    
    argocd_file_path = os.path.join(temp_dir, "argocd-application.yaml")
    with open(argocd_file_path, "w") as f:
        f.write(argocd_content)
        
    send_terminal_message(project_id, "⚓ Applying ArgoCD Application...\n\r")
    
    try:
        # Using kubectl to apply
        process = await asyncio.create_subprocess_exec(
            "kubectl", "apply", "-f", argocd_file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            send_terminal_message(project_id, "✅ ArgoCD Application Applied Successfully!\n\r")
        else:
            send_terminal_message(project_id, f"⚠️ ArgoCD Apply Failed: {stderr.decode()}\n\r")
            
    except FileNotFoundError:
        send_terminal_message(project_id, "⚠️ kubectl not found. Skipping ArgoCD application.\n\r")

    return {"k8s_status": "success", "gitops_repo": gitops_repo_url}
