# agents/monitor_agent.py
import asyncio
import aiohttp
from state import AgentState
from config.settings import settings

async def monitor_build_node(state: AgentState):
    """
    Polls the GitHub API to check if the Action we just triggered is successful.
    """
    owner = state["repo_owner"]
    repo = state["repo_name"]
    token = settings.github_token
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs"
    
    print(f"🕵️ Monitoring Builds for {owner}/{repo}...")

    # Poll for 60 seconds max
    for _ in range(6):
        await asyncio.sleep(10) # Wait 10s between checks
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    runs = data.get("workflow_runs", [])
                    if runs:
                        latest_run = runs[0]
                        status = latest_run.get("status")
                        conclusion = latest_run.get("conclusion")
                        
                        print(f"Build Status: {status} | Conclusion: {conclusion}")
                        
                        if status == "completed" and conclusion == "success":
                            return {"build_status": "success"}
                        if status == "completed" and conclusion == "failure":
                            return {"build_status": "failed"}
    
    return {"build_status": "timeout_or_pending"}