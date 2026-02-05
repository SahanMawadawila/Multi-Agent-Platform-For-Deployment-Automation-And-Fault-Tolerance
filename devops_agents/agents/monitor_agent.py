import asyncio
import aiohttp
from state import AgentState
from config.settings import settings
from app.kafka_terminal_producer import send_terminal_message

async def build_monitor_agent(state: AgentState):
    """
    Polls the GitHub API to check if the CI/CD build succeeded.
    Captures error logs on failure for potential retry/fix.
    """
    owner = state["repo_owner"]
    repo = state["repo_name"]
    project_id = state.get("project_id", "")
    token = settings.github_token
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    runs_url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs"
    
    print(f"🕵️ Monitoring Builds for {owner}/{repo}...")
    send_terminal_message(project_id, "🕵️ Monitoring build status...\n\r")

    # Poll for 5 minutes max (30 polls × 10 seconds)
    for i in range(30):
        await asyncio.sleep(10)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(runs_url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    runs = data.get("workflow_runs", [])
                    
                    if runs:
                        latest_run = runs[0]
                        status = latest_run.get("status")
                        conclusion = latest_run.get("conclusion")
                        run_id = latest_run.get("id")
                        
                        print(f"Build Status: {status} | Conclusion: {conclusion}")
                        
                        if status == "completed":
                            if conclusion == "success":
                                send_terminal_message(project_id, "✅ Build completed successfully!\n\r")
                                return {"build_status": "success"}
                            
                            if conclusion == "failure":
                                # Fetch error logs
                                error_logs = await fetch_build_logs(session, owner, repo, run_id, headers)
                                send_terminal_message(project_id, "❌ Build failed. Captured error logs.\n\r")
                                return {
                                    "build_status": "failed",
                                    "build_error_logs": error_logs
                                }
        
        # Progress update every 30 seconds
        if (i + 1) % 3 == 0:
            send_terminal_message(project_id, f"⏳ Still building... ({(i + 1) * 10}s elapsed)\n\r")
    
    send_terminal_message(project_id, "⏱️ Build monitoring timed out after 5 minutes.\n\r")
    return {"build_status": "timeout"}

async def fetch_build_logs(session, owner: str, repo: str, run_id: int, headers: dict) -> str:
    """Fetch workflow run logs from GitHub Actions."""
    try:
        # Get jobs for this run
        jobs_url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/jobs"
        async with session.get(jobs_url, headers=headers) as resp:
            if resp.status != 200:
                return "Failed to fetch job details"
            
            jobs_data = await resp.json()
            jobs = jobs_data.get("jobs", [])
            
            error_summary = []
            for job in jobs:
                if job.get("conclusion") == "failure":
                    job_name = job.get("name", "Unknown")
                    steps = job.get("steps", [])
                    
                    for step in steps:
                        if step.get("conclusion") == "failure":
                            step_name = step.get("name", "Unknown step")
                            error_summary.append(f"Job '{job_name}' failed at step: '{step_name}'")
            
            if error_summary:
                return "\n".join(error_summary)
            return "Build failed but no specific step failure found"
            
    except Exception as e:
        return f"Error fetching logs: {str(e)}"