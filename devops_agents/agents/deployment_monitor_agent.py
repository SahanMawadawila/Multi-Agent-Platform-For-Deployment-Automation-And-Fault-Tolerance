import asyncio
import subprocess
import requests
import json
from config.settings import settings
from app.kafka_terminal_producer import send_terminal_message

async def deployment_monitor_agent(state):
    """
    Deployment Monitor Agent:
    1. Waits for Kubernetes Deployment rollout.
    2. checks for Ingress/LoadBalancer URL.
    3. Performs Liveness Probe (HTTP Request).
    4. Updates final status in state.
    """
    project_id = state.get("project_id", "")
    analysis = state.get("analyzed_repository_details")
    
    send_terminal_message(project_id, "🔭 Starting Deployment Monitor...\n\r")
    
    namespace = project_id
    app_name = f"app-{project_id}"
    health_path = getattr(analysis, "health_check_path", "/")
    
    # Build the custom HTTPS URL
    access_url = f"https://{app_name}.{settings.domain_name}"
    
    # 1. Watch Rollout Status
    send_terminal_message(project_id, "⏳ Waiting for pod rollout...\n\r")
    try:
        # Wait for deployment resource to exist first (ArgoCD syncing takes time)
        send_terminal_message(project_id, "⏳ Waiting for ArgoCD sync...\n\r")
        for _ in range(30): # Wait up to 150s for resource creation
            check_proc = await asyncio.create_subprocess_exec(
                "kubectl", "get", "deployment", app_name, "-n", namespace,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await check_proc.communicate()
            if check_proc.returncode == 0:
                break
            await asyncio.sleep(5)
            
        # check rollout status
        process = await asyncio.create_subprocess_exec(
            "kubectl", "rollout", "status", f"deployment/{app_name}", "-n", namespace,
            "--timeout=300s",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            send_terminal_message(project_id, f"❌ Rollout failed: {stderr.decode()}\n\r")
            
            # Fetch logs for debugging
            logs_proc = await asyncio.create_subprocess_exec(
                "kubectl", "logs", f"deployment/{app_name}", "-n", namespace, "--tail=50",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            logs_out, _ = await logs_proc.communicate()
            
            return {
                "deployment_status": "failed", 
                "monitor_logs": logs_out.decode()
            }
            
        send_terminal_message(project_id, "✅ Pods are running!\n\r")

    except Exception as e:
        return {"deployment_status": "failed", "monitor_logs": str(e)}

    # 2. Display Access URL
    send_terminal_message(project_id, f"🌐 App URL: {access_url}\n\r")

    # 3. Liveness Check (Real HTTP Request)
    health_url = f"{access_url}{health_path}"
    send_terminal_message(project_id, f"💓 Checking Liveness: {health_url}\n\r")
    
    # Retry logic for application startup (DNS propagation + app startup time)
    is_healthy = False
    for _ in range(24): # Retry for 2 minutes (24 * 5s)
        try:
            send_terminal_message(project_id, f"💓 Probing: {health_url}\n\r")
            resp = await asyncio.to_thread(requests.get, health_url, timeout=10, verify=True)
            if resp.status_code == 200:
                is_healthy = True
                break
        except Exception:
            pass
        await asyncio.sleep(5)
    
    if is_healthy:
        send_terminal_message(project_id, f"🎉 Deployment Verified! App is live: {access_url}\n\r")
        return {
            "deployment_status": "success",
            "access_url": access_url
        }
    else:
        send_terminal_message(project_id, f"⚠️ App is deployed but health check failed at {health_url}\n\r")
        return {
            "deployment_status": "unhealthy", # Partial success
            "access_url": access_url
        }
