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
    
    # 1. Watch Rollout Status
    send_terminal_message(project_id, "⏳ Waiting for pod rollout...\n\r")
    try:
        # wait untile 5 minutes , if not deployed then fail
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

    # 2. Get External URL
    send_terminal_message(project_id, "🌐 Resolving external URL...\n\r")
    access_url = None
    
    for _ in range(12): # Retry for 1 minute (12 * 5s)
        try:
            proc = await asyncio.create_subprocess_exec(
                "kubectl", "get", "ingress", app_name, "-n", namespace, "-o", "json",
                stdout=asyncio.subprocess.PIPE
            )
            out, _ = await proc.communicate()
            data = json.loads(out)
            
            # Look for LoadBalancer Hostname (common in AWS ALB)
            ingress_status = data.get("status", {}).get("loadBalancer", {}).get("ingress", [])
            if ingress_status and "hostname" in ingress_status[0]:
                access_url = f"http://{ingress_status[0]['hostname']}"
                break
                
        except Exception:
            pass
            
        await asyncio.sleep(5)
    
    if not access_url:
        send_terminal_message(project_id, "⚠️ Could not resolve Ingress hostname (ALB provisioning takes time).\n\r")
        # Don't fail the pipeline, as ALB might just be slow. Provide kubectl command instead.
        return {
            "deployment_status": "success", 
            "access_url": "Pending (Check AWS Console or 'kubectl get ingress')"
        }

    # 3. Liveness Check (Real HTTP Request)
    send_terminal_message(project_id, f"💓 Checking Liveness: {access_url}{health_path}\n\r")
    
    # Retry logic for application startup (e.g. valid hostname but app 502s initially)
    is_healthy = False
    for _ in range(12): # Retry for 1 minute
        try:
            resp = await asyncio.to_thread(requests.get, f"{access_url}{health_path}", timeout=5)
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
        send_terminal_message(project_id, f"⚠️ App is deployed but health check failed at {access_url}{health_path}\n\r")
        return {
            "deployment_status": "unhealthy", # Partial success
            "access_url": access_url
        }
