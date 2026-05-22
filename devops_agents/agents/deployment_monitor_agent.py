import asyncio
import json
import time
from config.settings import settings
from app.kafka_terminal_producer import send_terminal_message

async def deployment_monitor_agent(state):
    project_id = state.get("project_id", "")
    
    send_terminal_message(project_id, "🔭 Starting Deployment Monitor (2-minute fast scan)...\n\r")
    
    namespace = project_id
    host = f"app-{project_id}.{settings.domain_name}"
    access_url = f"https://{host}"
    
    send_terminal_message(project_id, "⏳ Waiting for ArgoCD to sync and create pods...\n\r")
    await asyncio.sleep(15) 
    
    timeout = 120 # Reduced to 2 minutes
    start_time = time.time()
    
    # THE IGNORE ARRAY: Track pods that successfully spin up so we stop checking them
    healthy_pods = set()
    all_pods_ready = False
    
    while time.time() - start_time < timeout:
        proc = await asyncio.create_subprocess_exec(
            "kubectl", "get", "pods", "-n", namespace, "-o", "json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        
        if proc.returncode != 0:
            await asyncio.sleep(10)
            continue
            
        try:
            items = json.loads(stdout.decode()).get("items", [])
        except Exception:
            items = []
            
        if not items:
            send_terminal_message(project_id, "⏳ No pods found yet. Waiting...\n\r")
            await asyncio.sleep(10)
            continue
            
        all_pods_ready = True
        
        for pod in items:
            pod_name = pod["metadata"]["name"]
            
            # OPTIMIZATION: If we already confirmed this pod is healthy in a previous loop, skip it
            if pod_name in healthy_pods:
                continue
                
            phase = pod.get("status", {}).get("phase", "Unknown")
            container_statuses = pod.get("status", {}).get("containerStatuses", [])
            
            # Simplified readiness check
            is_ready = False
            if phase == "Succeeded":
                is_ready = True
            elif phase == "Running" and container_statuses:
                is_ready = all(c.get("ready", False) for c in container_statuses)
            
            if is_ready:
                # Add to ignore array and never check this specific pod again
                healthy_pods.add(pod_name)
                send_terminal_message(project_id, f"✅ Pod Ready: {pod_name}\n\r")
            else:
                # If even one pod is not ready, we cannot break the loop yet
                all_pods_ready = False
                
        # If every single pod in the namespace is now healthy, break the loop immediately
        if all_pods_ready:
            break
            
        await asyncio.sleep(10)
        
    # 2. Collect errors for ONLY the pods that failed
    aggregated_error_logs = ""
    
    if not all_pods_ready:
        send_terminal_message(project_id, "❌ Timeout reached. Gathering error logs for failed pods...\n\r")
        
        # Fetch the absolute final state of the pods
        proc = await asyncio.create_subprocess_exec(
            "kubectl", "get", "pods", "-n", namespace, "-o", "json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        
        try:
            items = json.loads(stdout.decode()).get("items", [])
        except Exception:
            items = []
            
        if not items:
            aggregated_error_logs += "Error: No pods were created in the namespace.\n"
        else:
            for pod in items:
                pod_name = pod["metadata"]["name"]
                
                # If a pod is NOT in our healthy_pods set, it's the one that failed
                if pod_name not in healthy_pods:
                    phase = pod.get("status", {}).get("phase", "Unknown")
                    send_terminal_message(project_id, f"📋 Fetching logs for unhealthy pod: {pod_name}\n\r")
                    
                    # Grab application logs
                    logs_proc = await asyncio.create_subprocess_exec(
                        "kubectl", "logs", pod_name, "-n", namespace, "--tail=100", "--all-containers",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    logs_out, logs_err = await logs_proc.communicate()
                    
                    # Grab Kubernetes events
                    events_proc = await asyncio.create_subprocess_exec(
                        "kubectl", "get", "events", "-n", namespace, "--field-selector", f"involvedObject.name={pod_name}",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    events_out, _ = await events_proc.communicate()
                    
                    aggregated_error_logs += f"=== Pod: {pod_name} ===\nPhase: {phase}\nEvents:\n{events_out.decode()}\nLogs:\n{logs_out.decode()[:2000]}\n{logs_err.decode()}\n\n"
                    
    # 3. Final Return
    if all_pods_ready:
        send_terminal_message(project_id, f"🎉 All deployments verified globally! Access: {access_url}\n\r")
        return {
            "deployment_status": "success",
            "access_url": access_url,
        }
    else:
        return {
            "deployment_status": "failed",
            "access_url": access_url,
            "deployment_error_logs": aggregated_error_logs
        }