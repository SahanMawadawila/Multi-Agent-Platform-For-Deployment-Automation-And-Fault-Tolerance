# agents/repo_analyst.py
from langchain_openai import ChatOpenAI  # Import OpenAI LLM wrapper
from langchain_core.tools import tool, InjectedToolArg  # Decorator to create tools
from langchain_core.messages import SystemMessage  # To set agent behavior
from langchain_core.runnables import RunnableConfig
from state import RepoAnalysisOutput  # Import the target output model
from tools.git_tools import AsyncGitTools  # Import our async git tools
from config.settings import settings  # Import settings
from typing import Annotated

# Initialize the LLM with the API key
llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.openai_key, temperature=0)

# Store local_path globally for the tool to access
_current_local_path: str = ""

def set_local_path(path: str):
    """Set the local path for tools to use."""
    global _current_local_path
    _current_local_path = path

# --- Define the Tool ---
@tool
async def read_repo_file(file_path: str) -> str:
    """
    Reads a specific file from the repository.
    Useful for checking package.json, requirements.txt, .env.example, etc.
    
    Args:
        file_path: The relative path to the file within the repository
    """
    global _current_local_path
    if not _current_local_path:
        return "Error: Internal path configuration missing."
    
    # Call the async read function
    content = await AsyncGitTools.read_file(_current_local_path, file_path)
    return content

# --- Setup the Agent ---
# The agent needs access to:
# 1. read_repo_file (to gather info)
# 2. RepoAnalysisOutput (to submit the final answer)
tools = [read_repo_file, RepoAnalysisOutput]

# Bind these tools to the LLM so it knows they exist
llm_with_tools = llm.bind_tools(tools)

async def repo_analysis_agent(state):
    """
    The Brain. Decides whether to read a file or submit final analysis.
    """
    # 1. Create the System Prompt (Identity & Instructions)
    system_prompt = SystemMessage(content="""
    You are a Senior DevOps Engineer. 
    Your goal is to analyze a codebase and extract deployment details.
    
    You have the list of files. 
    1. Look for config files (package.json, pom.xml, requirements.txt, .env).
    2. Use the 'read_repo_file' tool to read them.
    3. EXTRACT the following: Language, Framework, Port, Build Command, Run Command, Env Vars.
    
    Keep looping and reading files until you are 100% sure. 
    Once sure, call the 'RepoAnalysisOutput' tool to finish.
    """)

    current_count = state.get("loop_count", 0)

    if current_count > 5:
        return {
            "messages": [SystemMessage(content="ERROR: Loop limit reached.")],
            "loop_count": current_count # Don't increment further
        }
    
    # 2. Create the User Context (Current Situation)
    user_message = f"Here is the file list: {state['file_list']}"
    
    # 3. manage History: System Prompt + Previous Conversation (State) + New Context
    # We construct the message history for the LLM
    messages = [system_prompt] + state["messages"]
    
    # If this is the very first turn, append the file list context
    if len(state["messages"]) == 0:
        messages.append(SystemMessage(content=user_message))
        
    # 4. Invoke LLM
    response = await llm_with_tools.ainvoke(messages)
    
    # 5. Return the response (updates 'messages' in state automatically)
    return {"messages": [response], "loop_count": current_count + 1}