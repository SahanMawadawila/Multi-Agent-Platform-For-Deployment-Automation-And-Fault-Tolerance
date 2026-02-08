import os
import git
import asyncio
from typing import List
from config.settings import settings
import shutil

class AsyncGitTools:
    
    @staticmethod
    async def clone_repository(repo_url: str, clone_dir: str) -> str:
        def _clone():
            if os.path.exists(clone_dir):
                # If exists, pull latest 
                try:
                    repo = git.Repo(clone_dir)
                    repo.remotes.origin.pull()
                    return clone_dir
                except:
                    shutil.rmtree(clone_dir) # If pull fails, delete and try again

            auth_url = repo_url.replace("https://", f"https://{settings.github_token}@")
            git.Repo.clone_from(auth_url, clone_dir)
            
            # Configure Git user for commits
            repo = git.Repo(clone_dir)
            with repo.config_writer() as git_config:
                git_config.set_value('user', 'email', 'agent@bot.com')
                git_config.set_value('user', 'name', 'DevOps Agent')
            return clone_dir

        return await asyncio.to_thread(_clone)

    @staticmethod
    async def list_files(local_path: str) -> List[str]:
        def _walk():
            file_list = []
            for root, dirs, files in os.walk(local_path):
                if ".git" in root: continue #no need to go through git folder
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, local_path).replace("\\", "/")
                    file_list.append(rel_path)
            return file_list
        return await asyncio.to_thread(_walk)

    @staticmethod
    async def read_file(local_path: str, file_path: str) -> str:
        def _read():
            full_path = os.path.join(local_path, file_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        return f.read()
                except Exception as e: return str(e)
            return "File not found."
        return await asyncio.to_thread(_read)

    @staticmethod
    async def write_and_push(local_path: str, file_path: str, content: str, commit_message: str):
        """Writes a file, commits it, and pushes to origin."""
        def _push():
            full_path = os.path.join(local_path, file_path)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Write content
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            #stage, commit and push
            repo = git.Repo(local_path)
            repo.index.add([file_path]) 
            repo.index.commit(commit_message)
            origin = repo.remote(name='origin')
            origin.push()
            return "Pushed"

        return await asyncio.to_thread(_push)

    @staticmethod
    async def bulk_push(local_path: str, commit_message: str):
        """Stages all changes in the directory, commits, and pushes."""
        def _push():
            repo = git.Repo(local_path)
            # Stage all changes (new files, modifications, deletions)
            repo.git.add(A=True)
            
            # Check if there are changes to commit
            if repo.is_dirty() or repo.untracked_files:
                repo.index.commit(commit_message)
                origin = repo.remote(name='origin')
                origin.push()
                return "Pushed"
            return "No changes"

        return await asyncio.to_thread(_push)