import os
import shutil
from github import Github, GithubException # PyGithub
from git import Repo # GitPython

class GitMirrorSync:
    """
    Manages the creation and synchronization of a private mirror repository.
    """
    def __init__(self, platform_github_token, platform_org_name, workspace_dir="/tmp/git_mirror_workspace"):
        self.github_client = Github(platform_github_token)
        self.org_name = platform_org_name
        self.workspace_dir = workspace_dir
        self.token = platform_github_token

    def _get_auth_url(self, url):
        """Injects token into the URL so we can write to the private repo."""
        clean_url = url.replace("https://", "").replace("http://", "")
        return f"https://{self.token}@{clean_url}"

    def create_private_mirror(self, mirror_name):
        """
        Create the empty private repository on ORG account.
        """
        entity = self.github_client.get_organization(self.org_name)
        
        try:
            print(f"Creating private repo: {mirror_name}...")
            repo = entity.create_repo(
                name=mirror_name,
                private=True, 
                description="Automated Mirror Repository"
            )
            return repo.clone_url
        
        except GithubException as e:
            if e.status == 422: # Repo already exists
                print("Repo already exists, getting URL...")
                return entity.get_repo(mirror_name).clone_url
            raise e

    def sync_code(self, user_source_url, mirror_repo_name):
        """
        Clone User's code -> Push to Your Mirror.
        Works for BOTH initial setup AND updates.
        """
        
        # 1. Get the destination URL of YOUR private repo
        entity = self.github_client.get_organization(self.org_name)
      
        mirror_repo_url = entity.get_repo(mirror_repo_name).clone_url
        
        # Add Authentication to the push URL
        auth_mirror_url = self._get_auth_url(mirror_repo_url)

        # Define a temporary path in local filesystem to copy the repo
        local_path = os.path.join(self.workspace_dir, mirror_repo_name)

        # Clean up previous runs (to ensure we get a fresh copy)
        if os.path.exists(local_path):
            shutil.rmtree(local_path)

        print(f"🔄 Mirroring {user_source_url} -> {mirror_repo_name}...")

        # We use --bare because we don't need to see the files, we just want to move git history.
        repo = Repo.clone_from(user_source_url, local_path, bare=True)

        # Push to YOUR Private Repo
        new_remote = repo.create_remote('mirror_dest', auth_mirror_url)
        
        # push --mirror sends ALL branches and tags exactly as they are
        new_remote.push(mirror=True)
        
        print("✅ Sync Success!")
        
        # Cleanup (Optional: save disk space)
        shutil.rmtree(local_path)
        
        return mirror_repo_url
