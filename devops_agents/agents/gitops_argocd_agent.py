import os
import shutil
import stat
import asyncio
import subprocess
import base64
import boto3
from github import Github, Auth
from jinja2 import Environment, FileSystemLoader
from config.settings import settings
from app.kafka_terminal_producer import send_terminal_message
from tools.git_tools import AsyncGitTools


async def gitops_argocd_agent(state):
    """
    Post-processing graph node: handles GitOps repo + ArgoCD.
    
    1. Creates/reuses GitOps GitHub repo
    2. Configures ArgoCD repo secret
    3. Clones GitOps repo, copies app/ folder from temp dir
    4. Renders argocd-application.yaml at root (points to app/ path)
    5. Pushes everything
    6. Applies ArgoCD Application via kubectl
    """
    project_id = state.get("project_id", "")
    
    namespace = project_id
    gitops_repo_name = f"gitops-{project_id}"
    gitops_temp_dir = state.get("gitops_dir")
    
    # 1. GitHub Setup
    send_terminal_message(project_id, "📦 Setting up GitOps repository...\n\r")
    
    try:
        auth = Auth.Token(settings.github_token)
        g = Github(auth=auth)
        org = g.get_organization(settings.github_org)
        
        try:
            repo = org.get_repo(gitops_repo_name)
            send_terminal_message(project_id, f"✅ Found existing GitOps repo: {gitops_repo_name}\n\r")
        except Exception:
            send_terminal_message(project_id, f"✨ Creating new GitOps repo: {gitops_repo_name}\n\r")
            repo = org.create_repo(gitops_repo_name, private=True, auto_init=True)
        
        gitops_repo_url = repo.clone_url
        
    except Exception as e:
        send_terminal_message(project_id, f"❌ GitHub setup failed: {str(e)}\n\r")
        return {"deployment_status": "failed"}
    
    # 2. ArgoCD Repo Secret
    send_terminal_message(project_id, "🔐 Configuring ArgoCD with GitHub credentials...\n\r")
    secret_name = f"repo-{project_id}"
    subprocess.run(["kubectl", "delete", "secret", secret_name, "-n", "argocd"], 
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    cmd_secret = [
        "kubectl", "create", "secret", "generic", secret_name,
        "-n", "argocd",
        "--from-literal=type=git",
        f"--from-literal=url={gitops_repo_url}",
        f"--from-literal=password={settings.github_token}",
        f"--from-literal=username={settings.github_org or 'git'}"
    ]
    proc = subprocess.run(cmd_secret, capture_output=True, text=True)
    if proc.returncode != 0:
        send_terminal_message(project_id, f"⚠️ ArgoCD secret creation issue: {proc.stderr}\n\r")
    
    subprocess.run(["kubectl", "label", "secret", secret_name, "-n", "argocd", 
                    "argocd.argoproj.io/secret-type=repository"],
                   capture_output=True, text=True)
    
    send_terminal_message(project_id, "✅ ArgoCD Repository Secret configured.\n\r")
    
    # 3. Clone GitOps repo to a push directory
    push_dir = f"{gitops_temp_dir}_push"
    if os.path.exists(push_dir):
        shutil.rmtree(push_dir, onerror=lambda func, path, _: (os.chmod(path, stat.S_IWRITE), func(path)))
    
    send_terminal_message(project_id, "📥 Cloning GitOps repo...\n\r")
    await AsyncGitTools.clone_repository(gitops_repo_url, push_dir)
    
    # 4. Copy app/ folder from temp dir to push dir
    src_app_dir = os.path.join(gitops_temp_dir, "app")
    dst_app_dir = os.path.join(push_dir, "app")
    
    if os.path.exists(dst_app_dir):
        shutil.rmtree(dst_app_dir)
    
    if os.path.exists(src_app_dir):
        shutil.copytree(src_app_dir, dst_app_dir)
        send_terminal_message(project_id, "📂 Copied manifests to GitOps repo.\n\r")
    else:
        send_terminal_message(project_id, "⚠️ No app/ directory found in temp. Nothing to push.\n\r")
        return {"deployment_status": "failed"}
    
    # 5. Create ECR Image Pull Secret (once for all components)
    try:
        send_terminal_message(project_id, "🔐 Configuring K8s Image Pull Secret for ECR...\n\r")
        
        ecr = boto3.client(
            "ecr",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key,
            aws_secret_access_key=settings.aws_secret_key
        )
        token = ecr.get_authorization_token()
        username, password = base64.b64decode(
            token['authorizationData'][0]['authorizationToken']
        ).decode().split(':')
        server = token['authorizationData'][0]['proxyEndpoint']
        
        # Create namespace if not exists
        subprocess.run(["kubectl", "create", "namespace", namespace],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Delete existing secret (ECR tokens expire after 12 hours)
        subprocess.run(["kubectl", "delete", "secret", "regcred", "-n", namespace],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Create fresh secret
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
    
    # 6. Render ArgoCD Application at root (points to app/ path)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    templates_dir = os.path.join(base_dir, "templates", "k8s")
    env = Environment(loader=FileSystemLoader(templates_dir))
    argocd_template = env.get_template("argocd-application.j2")
    
    argocd_data = {
        "app_name": f"app-{project_id}",
        "namespace": namespace,
        "gitops_repo_url": gitops_repo_url,
    }
    argocd_content = argocd_template.render(argocd_data)
    
    # argocd-application.yaml goes at ROOT of GitOps repo (not inside app/)
    argocd_file_path = os.path.join(push_dir, "argocd-application.yaml")
    with open(argocd_file_path, "w") as f:
        f.write(argocd_content)
    
    # 7. Push everything
    send_terminal_message(project_id, "🚀 Pushing manifests to GitOps repo...\n\r")
    gitops_commit_id = await AsyncGitTools.bulk_push(push_dir, "Update K8s manifests")
    send_terminal_message(project_id, f"📌 GitOps commit: {gitops_commit_id[:7]}\n\r")
    
    # 7. Apply ArgoCD Application via kubectl
    send_terminal_message(project_id, "⚓ Applying ArgoCD Application...\n\r")
    
    try:
        process = await asyncio.create_subprocess_exec(
            "kubectl", "apply", "-f", argocd_file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=push_dir
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            send_terminal_message(project_id, "✅ ArgoCD Application Applied!\n\r")
        else:
            send_terminal_message(project_id, f"⚠️ ArgoCD Apply Failed: {stderr.decode()}\n\r")
    except FileNotFoundError:
        send_terminal_message(project_id, "⚠️ kubectl not found.\n\r")
    
    return {"gitops_commit_id": gitops_commit_id}
