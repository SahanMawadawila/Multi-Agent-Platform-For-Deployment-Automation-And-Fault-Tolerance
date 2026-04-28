import os
import git
import asyncio
from typing import List
from config.settings import settings
import shutil
import stat


def force_remove_readonly(func, path, exc_info):
    """Error handler for shutil.rmtree to handle read-only files on Windows."""
    os.chmod(path, stat.S_IWRITE)
    func(path)

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
                    shutil.rmtree(clone_dir, onerror=force_remove_readonly) # If pull fails, delete and try again

            auth_url = repo_url.replace("https://", f"https://{settings.github_token}@")
            git.Repo.clone_from(
                auth_url, clone_dir,
                multi_options=["--config core.longpaths=true"],
                allow_unsafe_options=True
            )
            
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
            ignore_dirs = {".git", "node_modules", "venv", ".venv", "__pycache__", "target", "dist", ".next"}
            for root, dirs, files in os.walk(local_path):
                # Modify dirs in-place to skip ignored directories
                dirs[:] = [d for d in dirs if d not in ignore_dirs]
                
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, local_path).replace("\\", "/")
                    file_list.append(rel_path)
            return file_list
        return await asyncio.to_thread(_walk)

    @staticmethod
    async def read_file(local_path: str, file_path: str, start_line: int = None, end_line: int = None) -> str:
        def _read():
            full_path = os.path.join(local_path, file_path)
            if os.path.exists(full_path):
                # Check file size before reading
                file_size = os.path.getsize(full_path)
                if file_size > 100 * 1024 and not start_line and not end_line:  # 100KB limit
                    return f"Error: File '{file_path}' is too large ({file_size} bytes). Reading files over 100KB is disabled to prevent context overflow. Please check the file list instead if you only need to know if it exists."

                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        
                        if start_line is not None or end_line is not None:
                            start_idx = max(0, start_line - 1) if start_line else 0
                            end_idx = end_line if end_line else len(lines)
                            selected_lines = lines[start_idx:end_idx]
                            
                            output_lines = [f"{i + start_idx + 1}: {line}" for i, line in enumerate(selected_lines)]
                            return "".join(output_lines)
                        
                        return "".join(lines)
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
            branch = repo.active_branch.name
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    origin.push(refspec=f"{branch}:{branch}", set_upstream=True)
                    return "Pushed"
                except git.exc.GitCommandError as e:
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(1) # Backoff before retry
                        repo.git.pull('origin', branch, rebase=True)
                    else:
                        raise e
            return "Pushed"

        return await asyncio.to_thread(_push)

    @staticmethod
    async def bulk_push(local_path: str, commit_message: str) -> str:
        """Stages all changes in the directory, commits, and pushes. Returns commit SHA."""
        def _push():
            repo = git.Repo(local_path)
            # Stage all changes (new files, modifications, deletions)
            repo.git.add(A=True)
            
            # Check if there are changes to commit
            if repo.is_dirty() or repo.untracked_files:
                commit = repo.index.commit(commit_message)
                origin = repo.remote(name='origin')
                branch = repo.active_branch.name
                
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        origin.push(refspec=f"{branch}:{branch}", set_upstream=True)
                        break
                    except git.exc.GitCommandError as e:
                        if attempt < max_retries - 1:
                            import time
                            time.sleep(1) # Backoff before retry
                            repo.git.pull('origin', branch, rebase=True)
                        else:
                            raise e
                            
                return str(repo.head.commit.hexsha)
            # Return current HEAD commit if no changes
            return str(repo.head.commit.hexsha)

        return await asyncio.to_thread(_push)

    @staticmethod
    async def create_and_checkout_branch(local_path: str, branch_name: str):
        """Create a new branch and check it out. If it already exists, just check it out."""
        def _branch():
            repo = git.Repo(local_path)
            if branch_name in repo.heads:
                repo.heads[branch_name].checkout()
            else:
                repo.create_head(branch_name).checkout()
        return await asyncio.to_thread(_branch)

    @staticmethod
    async def get_latest_commit_sha(local_path: str) -> str:
        """Get the SHA of the latest commit in the repository."""
        def _get_sha():
            repo = git.Repo(local_path)
            return str(repo.head.commit.hexsha)
        return await asyncio.to_thread(_get_sha)

    @staticmethod
    async def search_files(local_path: str, query: str) -> str:
        """Searches for a query string across the repository using git grep."""
        def _search():
            repo = git.Repo(local_path)
            try:
                # -n: line numbers, -I: ignore binary, -i: case insensitive, -e: pattern
                result = repo.git.grep('-n', '-I', '-i', '-e', query)
                
                # Truncate if too long to avoid context overflow for LLM
                if len(result) > 15000:
                    lines = result.split('\n')
                    truncated = '\n'.join(lines[:150]) + "\n... (truncated, refine your search query)"
                    return truncated
                return result
            except git.exc.GitCommandError as e:
                # git grep exits with 1 if no matches are found
                if e.status == 1:
                    return f"No matches found for '{query}'."
                return f"Error executing search: {str(e)}"
            except Exception as e:
                return f"Error executing search: {str(e)}"
        return await asyncio.to_thread(_search)