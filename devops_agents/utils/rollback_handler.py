"""
Rollback Handler - Handles skip_build=True rollbacks without running the full graph.
Reverts the GitOps repository to a previous commit and lets ArgoCD sync.
"""
import os
import shutil
import git
from config.settings import settings
from app.kafka_terminal_producer import send_terminal_message
from app.kafka_build_producer import send_build_event
from tools.git_tools import AsyncGitTools


async def handle_rollback(project_id: str, build_id: str, build_version: str, gitops_commit_id: str):
    """
    Handles rollback by reverting GitOps repo to the specified commit.
    ArgoCD will automatically sync and deploy the old version.
    """
    send_terminal_message(project_id, f"🔄 Starting rollback to version {build_version}...\\n\\r")
    
    if not gitops_commit_id:
        send_terminal_message(project_id, "❌ No GitOps commit ID found for this build. Cannot rollback.\\n\\r")
        send_build_event(project_id, build_id, "failed", details="Missing gitops_commit_id")
        return
    
    gitops_repo_name = f"gitops-{project_id}"
    gitops_repo_url = f"https://github.com/{settings.github_org}/{gitops_repo_name}.git"
    
    # Clone GitOps repo
    temp_dir = os.path.join(os.getcwd(), "temp", f"gitops_rollback_{project_id}")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    
    send_terminal_message(project_id, f"📥 Cloning GitOps repo...\\n\\r")
    
    try:
        await AsyncGitTools.clone_repository(gitops_repo_url, temp_dir)
        
        # Checkout the target commit
        repo = git.Repo(temp_dir)
        send_terminal_message(project_id, f"🔀 Checking out commit {gitops_commit_id[:7]}...\\n\\r")
        repo.git.checkout(gitops_commit_id)
        
        # Create a new branch or force push to main
        # For ArgoCD, we need to update the tracked branch (main)
        # Option: Create a rollback commit that reverts to the old state
        repo.git.checkout("main")
        repo.git.reset("--hard", gitops_commit_id)
        
        # Push force to update the branch
        send_terminal_message(project_id, "🚀 Pushing rollback changes to GitOps repo...\\n\\r")
        repo.git.push("--force", "origin", "main")
        
        send_terminal_message(project_id, f"✅ GitOps repo reverted to version {build_version}\\n\\r")
        send_terminal_message(project_id, "⏳ ArgoCD will now sync the old manifests...\\n\\r")
        
        # Send success event
        send_build_event(
            project_id, 
            build_id, 
            "success",
            details={
                "access_url": "",  # Will be resolved by ArgoCD
                "is_current": True,
                "gitops_commit_id": gitops_commit_id
            }
        )
        
        send_terminal_message(project_id, f"🎉 Rollback to version {build_version} complete!\\n\\r")
        
    except Exception as e:
        send_terminal_message(project_id, f"❌ Rollback failed: {str(e)}\\n\\r")
        send_build_event(project_id, build_id, "failed", details=str(e))
    
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
