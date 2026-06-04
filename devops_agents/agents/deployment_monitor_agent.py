import asyncio
import json
import re
import time
from config.settings import settings
from app.kafka_terminal_producer import send_terminal_message


def _extract_component_name(pod_name: str) -> str:
    """
    Extract the logical component name from a Kubernetes pod name.
    
    Pod names follow patterns like:
      - 'frontend-7c5cc979-j6sjm'          -> 'frontend'
      - 'account-service-57b98d4dd-tzqfq'   -> 'account-service'
      - 'account-service-postgres-0'         -> 'account-service-postgres'
      - 'rabbitmq-0'                         -> 'rabbitmq'
    
    Strategy: strip the trailing ReplicaSet hash and pod hash (or StatefulSet ordinal).
    """
    # StatefulSet pattern: name-0, name-1, etc.
    match = re.match(r"^(.+)-(\d+)$", pod_name)
    if match:
        return match.group(1)
    
    # Deployment pattern: name-<replicaset_hash>-<pod_hash>
    # ReplicaSet hash is typically 8-10 alphanumeric chars, pod hash is 5 chars
    match = re.match(r"^(.+)-[a-f0-9]{6,10}-[a-z0-9]{5}$", pod_name)
    if match:
        return match.group(1)
    
    # Fallback: just return as-is
    return pod_name


async def deployment_monitor_agent(state):
    project_id = state.get("project_id", "")
    
    send_terminal_message(project_id, "🔭 Starting Deployment Monitor (2-minute fast scan)...\n\r")
    
    namespace = project_id
    host = f"app-{project_id}.{settings.domain_name}"
    access_url = f"https://{host}"
    
    send_terminal_message(project_id, "⏳ Waiting for ArgoCD to sync and create pods...\n\r")
    await asyncio.sleep(15) 
    
    timeout = 240 # Reduced to 3 minutes
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
        
    # 2. Collect STRUCTURED errors for ONLY the pods that failed
    pod_error_list = []
    
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
            pod_error_list.append({
                "pod_name": "unknown",
                "component_name": "unknown",
                "phase": "Error",
                "events": "No pods were created in the namespace.",
                "logs": "",
            })
        else:
            # Use a dict to keep only the newest pod per component
            component_errors_dict = {}
            
            for pod in items:
                pod_name = pod["metadata"]["name"]
                
                # If a pod is NOT in our healthy_pods set, it's the one that failed
                if pod_name not in healthy_pods:
                    phase = pod.get("status", {}).get("phase", "Unknown")
                    component_name = _extract_component_name(pod_name)
                    creation_time = pod["metadata"].get("creationTimestamp", "")
                    
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
                    
                    pod_logs = logs_out.decode()[:2000]
                    if logs_err.decode().strip():
                        pod_logs += f"\nStderr: {logs_err.decode()[:500]}"
                    
                    new_error_record = {
                        "pod_name": pod_name,
                        "component_name": component_name,
                        "phase": phase,
                        "events": events_out.decode(),
                        "logs": pod_logs,
                        "creationTimestamp": creation_time,
                    }
                    
                    # Only replace if this pod is newer, or if we haven't seen this component yet
                    if component_name not in component_errors_dict:
                        component_errors_dict[component_name] = new_error_record
                    else:
                        existing_time = component_errors_dict[component_name]["creationTimestamp"]
                        if creation_time > existing_time:
                            component_errors_dict[component_name] = new_error_record

            for rec in component_errors_dict.values():
                # Remove the temporary timestamp before appending
                rec.pop("creationTimestamp", None)
                pod_error_list.append(rec)
                    
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
            "deployment_error_logs": pod_error_list,
        }