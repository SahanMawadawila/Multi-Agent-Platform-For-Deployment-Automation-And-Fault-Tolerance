from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.deps import get_current_user
from .deps import get_db
from app.models import UserProject
from app.config import settings
from kubernetes import client, config
import os

router = APIRouter()

@router.get("/{project_id}/diagram")
async def get_project_diagram(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Fetch Kubernetes resources (Pods, Services, Ingress) for a project/namespace
    and return a graph representation (nodes and edges) for the diagram.
    """
    # Verify project ownership
    result = await db.execute(
        select(UserProject).where(UserProject.project_id == project_id)
        .where(UserProject.owner_id == int(user["id"]))
    )
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Load K8s config
    try:
        # Try to load from KUBECONFIG env var/setting first
        if settings.KUBECONFIG and os.path.exists(settings.KUBECONFIG):
             config.load_kube_config(config_file=settings.KUBECONFIG)
        else:
            # Fallback to standard loading strategies
            try:
                config.load_kube_config()
            except config.ConfigException:
                # If running inside a cluster
                config.load_incluster_config()
    except Exception as e:
        print(f"Error loading K8s config: {e}")
        raise HTTPException(status_code=500, detail="Failed to load Kubernetes configuration")

    v1 = client.CoreV1Api()
    networking_v1 = client.NetworkingV1Api()
    
    # Requirement: use project_id as namespace
    namespace = project_id 
    
    nodes = []
    edges = []
    
    try:
        # Get Pods
        pods = v1.list_namespaced_pod(namespace=namespace)
        pod_map = {pod.metadata.name: pod for pod in pods.items}
        
        for pod in pods.items:
            # Determine type based on name
            pod_name = pod.metadata.name.lower()
            resource_type = "other"
            if "app" in pod_name:
                resource_type = "app"
            elif "db" in pod_name or "database" in pod_name or "postgres" in pod_name or "mysql" in pod_name or "mongo" in pod_name:
                 resource_type = "database"

            nodes.append({
                "id": pod.metadata.name,
                "data": {
                    "label": pod.metadata.name, 
                    "status": pod.status.phase,
                    "kind": "Pod",
                    "type": resource_type
                }
            })
            
        # Get Services & Ingresses to determine connections
        services = v1.list_namespaced_service(namespace=namespace)
        ingresses = networking_v1.list_namespaced_ingress(namespace=namespace)
        
        # Build connections: Load Balancer -> Ingress -> Service -> Pod
        # Simplification: If Ingress points to Service, and Service selects Pod, 
        # then Logic: LoadBalancer -> Pod
        
        exposed_pods = set()

        for ing in ingresses.items:
             if ing.spec.rules:
                 for rule in ing.spec.rules:
                     if rule.http and rule.http.paths:
                         for path in rule.http.paths:
                             if path.backend and path.backend.service:
                                 service_name = path.backend.service.name
                                 
                                 # Find the service
                                 target_svc = next((s for s in services.items if s.metadata.name == service_name), None)
                                 if target_svc and target_svc.spec.selector:
                                     # Find pods selected by this service
                                     for pod in pods.items:
                                        match = True
                                        for k, v in target_svc.spec.selector.items():
                                            val = pod.metadata.labels.get(k) if pod.metadata.labels else None
                                            if val != v:
                                                match = False
                                                break
                                        if match:
                                            exposed_pods.add(pod.metadata.name)
        
        # Add edges for exposed pods (LB -> Pod)
        for pod_name in exposed_pods:
            edges.append({
                "id": f"lb-{pod_name}",
                "source": "load-balancer", # Logical starting point
                "target": pod_name,
                "type": "ingress"
            })
            
        # Add edges for App -> Database
        app_pods = [p["id"] for p in nodes if p["data"]["type"] == "app"]
        db_pods = [p["id"] for p in nodes if p["data"]["type"] == "database"]
        
        for app in app_pods:
            for db in db_pods:
                 edges.append({
                    "id": f"{app}-{db}",
                    "source": app,
                    "target": db,
                    "type": "internal"
                })


    except client.exceptions.ApiException as e:
        print(f"K8s API error: {e}")
        if e.status == 404:
             # Namespace not found implies no resources deployed yet
             return {"nodes": [], "edges": []}
        raise HTTPException(status_code=500, detail=f"Kubernetes API error: {e}")
    except Exception as e:
        print(f"Error fetching K8s resources: {e}")
        raise HTTPException(status_code=500, detail="Error generating diagram")

    return {"nodes": nodes, "edges": edges}
