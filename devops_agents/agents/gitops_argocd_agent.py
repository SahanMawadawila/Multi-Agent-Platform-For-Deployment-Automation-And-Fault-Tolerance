import os
import shutil
import asyncio
import subprocess
from github import Github, Auth
from jinja2 import Environment, FileSystemLoader
from config.settings import settings
from app.kafka_terminal_producer import send_terminal_message
from tools.git_tools import AsyncGitTools


async def gitops_argocd_agent(state):
    """
    Post-processing graph node: handles GitOps repo creation, manifest push, and ArgoCD application.
    1. Creates/reuses GitOps GitHub repo
    2. Configures ArgoCD repo secret
    3. Copies all manifests from temp/gitops_{project_id}/ to GitOps repo
    4. Pushes manifests
    5. Applies ArgoCD Application
    """
    project_id = state.get("project_id", "")
    
    namespace = project_id
    gitops_repo_name = f"gitops-{project_id}"
    gitops_dir = os.path.join(os.getcwd(), "temp", f"gitops_{project_id}")
    
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
    
    # 3. Clone GitOps repo and copy manifests
    push_dir = os.path.join(os.getcwd(), "temp", f"gitops_{project_id}_push")
    if os.path.exists(push_dir):
        shutil.rmtree(push_dir)
    
    send_terminal_message(project_id, "📥 Cloning GitOps repo...\n\r")
    await AsyncGitTools.clone_repository(gitops_repo_url, push_dir)
    
    # Copy everything from gitops_dir to push_dir/app/
    app_dir = os.path.join(push_dir, "app")
    if os.path.exists(app_dir):
        shutil.rmtree(app_dir)
    os.makedirs(app_dir, exist_ok=True)
    
    for item in os.listdir(gitops_dir):
        src = os.path.join(gitops_dir, item)
        dst = os.path.join(app_dir, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
    
    # 4. Push manifests
    send_terminal_message(project_id, "🚀 Pushing manifests to GitOps repo...\n\r")
    gitops_commit_id = await AsyncGitTools.bulk_push(push_dir, "Update K8s manifests")
    send_terminal_message(project_id, f"📌 GitOps commit: {gitops_commit_id[:7]}\n\r")
    
    # 5. Apply ArgoCD Application
    templates_dir = os.path.join(os.getcwd(), "templates", "k8s")
    env = Environment(loader=FileSystemLoader(templates_dir))
    argocd_template = env.get_template("argocd-application.j2")
    
    argocd_data = {
        "app_name": f"app-{project_id}",
        "namespace": namespace,
        "gitops_repo_url": gitops_repo_url,
    }
    argocd_content = argocd_template.render(argocd_data)
    
    argocd_file_path = os.path.join(push_dir, "argocd-application.yaml")
    with open(argocd_file_path, "w") as f:
        f.write(argocd_content)
    
    send_terminal_message(project_id, "⚓ Applying ArgoCD Application...\n\r")
    
    try:
        process = await asyncio.create_subprocess_exec(
            "kubectl", "apply", "-f", argocd_file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            send_terminal_message(project_id, "✅ ArgoCD Application Applied!\n\r")
        else:
            send_terminal_message(project_id, f"⚠️ ArgoCD Apply Failed: {stderr.decode()}\n\r")
    except FileNotFoundError:
        send_terminal_message(project_id, "⚠️ kubectl not found.\n\r")
    
    return {"gitops_commit_id": gitops_commit_id}
