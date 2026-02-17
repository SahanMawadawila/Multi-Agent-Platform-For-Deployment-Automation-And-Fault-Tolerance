import asyncio
import aiohttp
import git
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
    build_id = state.get("build_id", "")
    local_path = state["local_path"]
    token = settings.github_token
    component_name = state.get("component_name")
    
    # Get the current commit SHA to monitor the correct build
    try:
        git_repo = git.Repo(local_path)
        current_sha = git_repo.head.commit.hexsha
    except Exception as e:
        print(f"Error getting git info: {e}")
        current_sha = None

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    runs_url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs"
    
    print(f"🕵️ Monitoring Builds for {owner}/{repo} (SHA: {current_sha[:7] if current_sha else 'Latest'})...")
    send_terminal_message(project_id, f"🕵️ Monitoring build status for commit {current_sha[:7] if current_sha else 'latest'}...\n\r", component_name)

    # Poll for 5 minutes max (30 polls × 10 seconds)
    import datetime
    start_time = datetime.datetime.now(datetime.timezone.utc)
    for i in range(30):
        await asyncio.sleep(10)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(runs_url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    runs = data.get("workflow_runs", [])
                    
                    target_run = None
                    # Attempt 1: Match by SHA
                    if current_sha:
                        matching_runs = [r for r in runs if r.get("head_sha") == current_sha]
                        if matching_runs:
                            target_run = matching_runs[0]
                    
                    # Attempt 2: If SHA not found, check if latest run is active or new
                    if not target_run and runs:
                        latest_run = runs[0]
                        run_status = latest_run.get("status")
                        
                        # Check if created after we started monitoring (with 1 min buffer for clock skew)
                        created_at_str = latest_run.get("created_at") # ISO format
                        try:
                            created_at = datetime.datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                            is_new = created_at > (start_time - datetime.timedelta(minutes=1))
                        except Exception:
                            is_new = False

                        if run_status in ["queued", "in_progress"] or is_new:
                            target_run = latest_run
                            if current_sha: 
                                print(f"⚠️ SHA match failed. Falling back to latest run {target_run.get('id')} (Status: {run_status})")

                    if target_run:
                        status = target_run.get("status")
                        conclusion = target_run.get("conclusion")
                        run_id = target_run.get("id")
                        
                        print(f"Run ID: {run_id} | Status: {status} | Conclusion: {conclusion}")
                        
                        if status == "completed":
                            if conclusion == "success":
                                send_terminal_message(project_id, "✅ Build completed successfully!\n\r", component_name)
                                return {"build_status": "success"}
                            
                            if conclusion != "success": # Catch failure, cancelled, timed_out, etc.
                                # Fetch error logs
                                error_logs = await fetch_build_logs(session, owner, repo, run_id, headers)
                                send_terminal_message(project_id, f"❌ Build finished with status: {conclusion}. Captured logs.\n\r", component_name)
                                return {
                                    "build_status": "failed",
                                    "build_error_logs": error_logs
                                }
                else:
                    print(f"Failed to fetch workflow runs: HTTP {resp.status}")
                    print(await resp.text())
        
        # Progress update every 30 seconds
        if (i + 1) % 3 == 0:
            send_terminal_message(project_id, f"⏳ Still building... ({(i + 1) * 10}s elapsed)\n\r", component_name)
    
    send_terminal_message(project_id, "⏱️ Build monitoring timed out after 5 minutes.\n\r", component_name)
    return {"build_status": "timeout"}

async def fetch_build_logs(session, owner: str, repo: str, run_id: int, headers: dict) -> str:
    """Fetch workflow run logs from GitHub Actions."""
    try:
        # Get jobs for this run
        print(f"Fetching job details for run {run_id}...")
        jobs_url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/jobs"
        async with session.get(jobs_url, headers=headers) as resp:
            if resp.status != 200:
                return "Failed to fetch job details"
            
            jobs_data = await resp.json()
            jobs = jobs_data.get("jobs", [])
            
            error_details = []
            print(f"Found {len(jobs)} jobs. Checking for failures...")
            for job in jobs:
                if job.get("conclusion") == "failure":
                    job_name = job.get("name", "Unknown")
                    job_id = job.get("id")
                    
                    # Method 1: Get raw logs
                    logs_url = f"https://api.github.com/repos/{owner}/{repo}/actions/jobs/{job_id}/logs"
                    try:
                        async with session.get(logs_url, headers=headers) as log_resp:
                            if log_resp.status == 200:
                                log_text = await log_resp.text()
                                # Get last 50 lines of logs
                                log_lines = log_text.splitlines()[-50:]
                                error_details.append(f"--- Logs for Job: {job_name} ---\n" + "\n".join(log_lines))
                    except Exception as log_ex:
                        error_details.append(f"Could not fetch raw logs for {job_name}: {log_ex}")

                    # Method 2: Check steps (Fallback/Additional context)
                    steps = job.get("steps", [])
                    for step in steps:
                        if step.get("conclusion") == "failure":
                            step_name = step.get("name", "Unknown step")
                            error_details.append(f"Job '{job_name}' failed at step: '{step_name}'")
            
            if error_details:
                return "\n\n".join(error_details)
            return "Build failed but no specific failure details found"
            
    except Exception as e:
        return f"Error fetching logs: {str(e)}"