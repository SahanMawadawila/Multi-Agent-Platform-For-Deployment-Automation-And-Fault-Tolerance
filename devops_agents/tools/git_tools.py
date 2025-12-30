# tools/git_tools.py
import os  # Used for file system path manipulation
import git  # The GitPython library for git operations
import asyncio  # Used to run blocking code asynchronously
from typing import List  # Type hinting for list returns
from config.settings import settings  # Import our central settings

class AsyncGitTools:
    """
    Asynchronous wrapper around Git operations.
    Using asyncio.to_thread to prevent blocking the event loop.
    """

    @staticmethod
    async def clone_repository(repo_url: str, clone_dir: str) -> str:
        """
        Clones a Git repository to the specified directory asynchronously.
        """
        # Define the blocking sync function inside
        def _clone():
            # Check if directory already exists to prevent errors
            if not os.path.exists(clone_dir):
                # Inject token into URL for authentication: https://TOKEN@github.com/...
                # We strip 'https://' first to insert the token correctly
                auth_url = repo_url.replace("https://", f"https://{settings.github_token}@")
                # Perform the clone operation
                git.Repo.clone_from(auth_url, clone_dir)
            return clone_dir

        # Run the blocking function in a separate thread and await result
        return await asyncio.to_thread(_clone)

    @staticmethod
    async def list_files(local_path: str) -> List[str]:
        """
        Returns a list of all files to help agent understand repo structure.
        """
        # Define the blocking sync function inside
        def _walk():
            file_list = []
            # Walk through every directory and file in the path
            for root, dirs, files in os.walk(local_path):
                # Skip .git directory to avoid confusing the agent
                if ".git" in root:
                    continue
                for file in files:
                    # Create full path
                    full_path = os.path.join(root, file)
                    # Remove the base local_path to return relative paths (e.g., "src/index.js")
                    relative_path = os.path.relpath(full_path, local_path)
                    # Normalize to forward slashes for consistency
                    relative_path = relative_path.replace("\\", "/")
                    file_list.append(relative_path)
            return file_list

        # Run in separate thread
        return await asyncio.to_thread(_walk)

    @staticmethod
    async def read_file(local_path: str, file_path: str) -> str:
        """
        Reads the content of a file in the local repository.
        """
        # Define the blocking sync function inside
        def _read():
            # Normalize the file path - handle both forward and backslashes
            # Also strip leading slashes/backslashes
            normalized_file_path = file_path.lstrip("/\\").replace("\\", "/")
            
            # Construct the full absolute path using os.path.join for cross-platform compatibility
            full_path = os.path.join(local_path, normalized_file_path)
            
            # Normalize the path for the current OS
            full_path = os.path.normpath(full_path)
            
            print(f"📂 Attempting to read: {full_path}")  # Debug logging
            
            # Check if file exists before opening
            if os.path.exists(full_path):
                try:
                    # Open file in read mode with utf-8 encoding
                    with open(full_path, 'r', encoding='utf-8') as file:
                        return file.read()
                except Exception as e:
                    # Return error message so agent knows reading failed
                    return f"Error reading file: {str(e)}"
            return f"File not found: {full_path}"

        # Run in separate thread
        return await asyncio.to_thread(_read)