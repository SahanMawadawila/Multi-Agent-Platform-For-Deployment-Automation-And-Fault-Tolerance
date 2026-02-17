import os
import asyncio
from config.settings import settings
from app.kafka_terminal_producer import send_terminal_message


# Bitnami Helm chart configs for each DB type
HELM_CONFIGS = {
    "mongodb": {
        "chart": "oci://registry-1.docker.io/bitnamicharts/mongodb",
        "set_values": [
            "auth.rootPassword=agentDbPass123",
            "persistence.size=1Gi",
        ],
    },
    "postgres": {
        "chart": "oci://registry-1.docker.io/bitnamicharts/postgresql",
        "set_values": [
            "auth.postgresPassword=agentDbPass123",
            "primary.persistence.size=1Gi",
        ],
    },
    "mysql": {
        "chart": "oci://registry-1.docker.io/bitnamicharts/mysql",
        "set_values": [
            "auth.rootPassword=agentDbPass123",
            "primary.persistence.size=1Gi",
        ],
    },
}


async def database_deployment_agent(state):
    """
    Database Manifest Generator Agent.
    Uses `helm template` to render Bitnami chart YAML without deploying.
    ArgoCD will deploy them alongside app manifests.
    
    Paths:
      - Single project: temp/gitops_{project_id}/app/{database_type}.yaml
      - Multi-project:  temp/gitops_{project_id}/app/{component_name}-db/{database_type}.yaml
    
    No-op if needs_database is False.
    """
    project_id = state.get("project_id", "")
    component_name = state.get("component_name")
    is_multi_project = state.get("is_multi_project", False)
    needs_database = state.get("needs_database", False)
    database_type = state.get("database_type", "")
    
    if not needs_database:
        send_terminal_message(project_id, "ℹ️ No database needed. Skipping.\n\r", component_name)
        return {"database_deployed": False}
    
    config = HELM_CONFIGS.get(database_type)
    if not config:
        send_terminal_message(project_id, f"⚠️ Unknown database type: {database_type}. Skipping.\n\r", component_name)
        return {"database_deployed": False}
    
    # Release name for helm template
    if component_name:
        release_name = f"{component_name}-db"
    else:
        release_name = f"app-db"
    namespace = project_id
    
    send_terminal_message(project_id, f"📦 Generating {database_type} manifests via Helm template...\n\r", component_name)
    
    # Build helm template command
    cmd = [
        "helm", "template", release_name, config["chart"],
        "--namespace", namespace,
    ]
    for sv in config["set_values"]:
        cmd.extend(["--set", sv])
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode().strip()
            send_terminal_message(project_id, f"❌ Helm template failed: {error_msg}\n\r", component_name)
            return {"database_deployed": False, "build_status": "db_manifest_failed"}
        
        rendered_yaml = stdout.decode()
        
        # Determine output path (same folder as component manifests):
        #   Single:  temp/gitops_{project_id}/app/{database_type}.yaml
        #   Multi:   temp/gitops_{project_id}/app/{component_name}/{database_type}.yaml
        gitops_base = os.path.join(os.getcwd(), "temp", f"gitops_{project_id}")
        if is_multi_project and component_name:
            db_manifests_path = os.path.join(gitops_base, "app", component_name)
        else:
            db_manifests_path = os.path.join(gitops_base, "app")
        os.makedirs(db_manifests_path, exist_ok=True)
        
        output_file = os.path.join(db_manifests_path, f"{database_type}.yaml")
        with open(output_file, "w") as f:
            f.write(rendered_yaml)
        
        label = f"{component_name}/{database_type}.yaml" if component_name else f"{database_type}.yaml"
        send_terminal_message(project_id, f"✅ Database manifests generated: {label}\n\r", component_name)
        
        return {
            "database_deployed": True,
            "database_service_name": release_name,
        }
        
    except FileNotFoundError:
        send_terminal_message(project_id, "❌ Helm CLI not found. Cannot generate database manifests.\n\r", component_name)
        return {"database_deployed": False, "build_status": "helm_not_found"}
    except Exception as e:
        send_terminal_message(project_id, f"❌ Database manifest generation failed: {str(e)}\n\r", component_name)
        return {"database_deployed": False}
