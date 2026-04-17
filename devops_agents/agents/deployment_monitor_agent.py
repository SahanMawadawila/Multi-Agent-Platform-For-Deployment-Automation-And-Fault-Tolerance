import asyncio
import requests
from config.settings import settings
from app.kafka_terminal_producer import send_terminal_message


async def deployment_monitor_agent(state):
    """
    Post-processing graph node: monitors ALL component deployments.
    Waits for ArgoCD sync + rollout, performs liveness probe.
    Works for both single and multi-project.
    """
    project_id = state.get("project_id", "")
    components = state.get("components", [])
    
    send_terminal_message(project_id, "🔭 Starting Deployment Monitor...\n\r")
    
    namespace = project_id
    host = f"app-{project_id}.{settings.domain_name}"
    access_url = f"https://{host}"
    
    all_healthy = True
    
    for comp in components:
        app_name = comp.get("name") or "app"
        comp_name = comp.get("name", "")
        health_path = comp.get("health_check_path", "/")
        
        send_terminal_message(project_id, f"⏳ Waiting for {app_name} rollout...\n\r", comp_name)
        
        # 1. Wait for deployment resource to exist (ArgoCD sync time)
        for _ in range(30):
            check_proc = await asyncio.create_subprocess_exec(
                "kubectl", "get", "deployment", app_name, "-n", namespace,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await check_proc.communicate()
            if check_proc.returncode == 0:
                break
            await asyncio.sleep(5)
        
        # 2. Watch rollout status
        process = await asyncio.create_subprocess_exec(
            "kubectl", "rollout", "status", f"deployment/{app_name}",
            "-n", namespace, "--timeout=300s",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            send_terminal_message(project_id, f"❌ {app_name} rollout failed: {stderr.decode()}\n\r", comp_name)
            
            # Fetch logs for debugging
            logs_proc = await asyncio.create_subprocess_exec(
                "kubectl", "logs", f"deployment/{app_name}", "-n", namespace, "--tail=50",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            logs_out, _ = await logs_proc.communicate()
            send_terminal_message(project_id, f"📋 Logs: {logs_out.decode()[:500]}\n\r", comp_name)
            
            all_healthy = False
            continue
        
        send_terminal_message(project_id, f"✅ {app_name} pods are running!\n\r", comp_name)
        
        # 3. Liveness check
        health_url = f"{access_url}{health_path}"
        send_terminal_message(project_id, f"💓 Checking liveness: {health_url}\n\r", comp_name)
        
        is_healthy = False
        for _ in range(24):  # Retry for 2 minutes
            try:
                resp = await asyncio.to_thread(requests.get, health_url, timeout=10, verify=True)
                if resp.status_code == 200:
                    is_healthy = True
                    break
            except Exception:
                pass
            await asyncio.sleep(5)
        
        if is_healthy:
            send_terminal_message(project_id, f"🎉 {app_name} is live!\n\r", comp_name)
        else:
            send_terminal_message(project_id, f"⚠️ {app_name} deployed but health check failed.\n\r", comp_name)
    
    # Final result
    if all_healthy:
        send_terminal_message(project_id, f"🎉 All deployments verified! Access: {access_url}\n\r")
        return {
            "deployment_status": "success",
            "access_url": access_url,
        }
    else:
        send_terminal_message(project_id, "⚠️ Some deployments had issues.\n\r")
        return {
            "deployment_status": "failed",
            "access_url": access_url,
        }
