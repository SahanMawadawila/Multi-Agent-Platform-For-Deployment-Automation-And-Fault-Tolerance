import os
import shutil
import stat
import time
import gc
from github import Github, GithubException # PyGithub
from git import Repo # GitPython
from urllib.parse import quote

class GitMirrorSync:
    """
    Manages the creation and synchronization of a private mirror repository.
    """
    def __init__(self, platform_github_token, platform_org_name, workspace_dir=None):
        self.github_client = Github(platform_github_token)
        self.org_name = platform_org_name
        # Use a Windows-compatible temp directory
        if workspace_dir:
            self.workspace_dir = workspace_dir
        else:
            # Use system temp directory for better Windows compatibility
            import tempfile
            self.workspace_dir = os.path.join(tempfile.gettempdir(), "git_mirror_workspace")
        self.token = platform_github_token
        
        # Ensure workspace directory exists
        os.makedirs(self.workspace_dir, exist_ok=True)

    def _get_auth_url(self, url):
        """Injects token into the URL so we can write to the private repo.

        URL-encode the token to avoid breaking the URL when token contains
        special characters.
        """
        if not self.token:
            return url

        # Only inject for HTTP/HTTPS URLs
        if url.startswith("https://") or url.startswith("http://"):
            clean_url = url.replace("https://", "").replace("http://", "")
            token_enc = quote(self.token, safe='')
            return f"https://{token_enc}@{clean_url}"

        return url

    def _inject_token_into_url(self, url, token):
        """Return a clone URL that includes the provided access token for HTTPS URLs.

        If the provided URL is not HTTP(S) (e.g. an SSH URL), return the original URL.
        """
        if not token:
            return url

        # Only inject for HTTP/HTTPS URLs; URL-encode token to avoid breaking
        if url.startswith("https://") or url.startswith("http://"):
            clean = url.replace("https://", "").replace("http://", "")
            token_enc = quote(token, safe='')
            return f"https://{token_enc}@{clean}"

        # Can't inject token into SSH or other URL schemes; return original
        return url

    def _force_remove_readonly(self, func, path, excinfo):
        """
        Error handler for shutil.rmtree on Windows.
        Removes read-only attribute and retries deletion.
        """
        os.chmod(path, stat.S_IWRITE)
        func(path)

    def _safe_rmtree(self, path, max_retries=3):
        """
        Safely remove a directory tree on Windows.
        Handles locked files by Git.
        """
        for attempt in range(max_retries):
            try:
                if os.path.exists(path):
                    # Force garbage collection to release file handles
                    gc.collect()
                    time.sleep(0.5)  # Give OS time to release handles
                    
                    # Use onexc (Python 3.12+) or onerror for older versions
                    shutil.rmtree(path, onexc=self._force_remove_readonly)
                return True
            except PermissionError as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ Retry {attempt + 1}/{max_retries}: Waiting for file handles to release...")
                    time.sleep(1)
                else:
                    print(f"⚠️ Could not delete {path}: {e}. Will be cleaned up later.")
                    return False
        return False

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

    def sync_code(self, user_source_url, mirror_repo_name, env_variables: dict = None, source_access_token: str = None):
        """
        Clone User's code -> Add .env if provided -> Push to Your Mirror.
        Works for BOTH initial setup AND updates.
        
        Args:
            user_source_url: URL of the user's source repository
            mirror_repo_name: Name of the mirror repository
            env_variables: Optional dict of environment variables to create .env file
        """
        
        # 1. Get the destination URL of YOUR private repo
        entity = self.github_client.get_organization(self.org_name)
      
        mirror_repo_url = entity.get_repo(mirror_repo_name).clone_url
        
        # Add Authentication to the push URL
        auth_mirror_url = self._get_auth_url(mirror_repo_url)

        # Define a temporary path in local filesystem to copy the repo
        local_path = os.path.join(self.workspace_dir, mirror_repo_name)

        # Clean up previous runs (to ensure we get a fresh copy)
        self._safe_rmtree(local_path)

        print(f"🔄 Mirroring {user_source_url} -> {mirror_repo_name}...")

        # If a source access token is provided, inject it into the clone URL for HTTPS repos.
        clone_url = user_source_url
        if source_access_token:
            injected = self._inject_token_into_url(user_source_url, source_access_token)
            if injected != user_source_url:
                clone_url = injected
                print("Using provided access token for cloning (token not shown).")
            else:
                print("Provided access token could not be injected (non-HTTPS URL); proceeding without injecting token.")

        repo = None
        try:
            # Clone normally (not bare) so we can add files
            print("Cloning source repository...")
            repo = Repo.clone_from(clone_url, local_path)
            print("✅ Clone Success!", local_path)

            # Try to determine the latest commit on origin/main (or fallbacks)
            commit_id = None
            try:
                # Ensure we have fetched remote refs
                try:
                    repo.remotes.origin.fetch()
                except Exception:
                    pass

                for remote_ref in ("origin/main", "origin/master"):
                    try:
                        commit_id = repo.commit(remote_ref).hexsha
                        break
                    except Exception:
                        continue

                # Fallback to local HEAD if remote refs not present
                if not commit_id:
                    try:
                        commit_id = repo.head.commit.hexsha
                    except Exception:
                        commit_id = None
            except Exception:
                commit_id = None

            # Add .env file if env_variables provided
            if env_variables:
                self._create_env_file(local_path, env_variables)
                # Stage and commit the .env file
                repo.index.add(['.env'])
                repo.index.commit("Add environment variables")
                print("✅ Added .env file to repository")

            # Push to YOUR Private Repo
            new_remote = repo.create_remote('mirror_dest', auth_mirror_url)
            
            # Push all branches
            new_remote.push(refspec='refs/heads/*:refs/heads/*', force=True)
            # Push all tags
            new_remote.push(tags=True, force=True)
            
            print("✅ Sync Success!", f"commit={commit_id}")
            
        finally:
            # Close the repo to release file handles
            if repo:
                repo.close()
                del repo
            
            # Cleanup (Optional: save disk space)
            self._safe_rmtree(local_path)
        
        # Return mirror URL and the commit id we synced (may be None if unknown)
        return mirror_repo_url, commit_id

    def _create_env_file(self, repo_path: str, env_variables: dict):
        """
        Create a .env file in the repository directory.
        
        Args:
            repo_path: Path to the local repository
            env_variables: Dictionary of {KEY: value} pairs
        """
        env_file_path = os.path.join(repo_path, '.env')
        
        lines = []
        lines.append("# Auto-generated environment variables")
        lines.append("# Generated by Flow Pilot AI")
        lines.append("")
        
        for key, value in env_variables.items():
            # Handle values with spaces or special characters
            if isinstance(value, str) and (' ' in value or '"' in value or "'" in value):
                escaped_value = value.replace('"', '\\"')
                lines.append(f'{key}="{escaped_value}"')
            else:
                lines.append(f"{key}={value}")
        
        with open(env_file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"📝 Created .env file at {env_file_path}")