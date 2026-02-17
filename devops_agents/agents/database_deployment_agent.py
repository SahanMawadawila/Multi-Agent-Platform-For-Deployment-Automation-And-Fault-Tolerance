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
    Writes generated YAML to temp/gitops_{project_id}/{component}-db/
    ArgoCD will deploy them alongside app manifests.
    
    No-op if needs_database is False.
    """
    project_id = state.get("project_id", "")
    component_name = state.get("component_name")
    needs_database = state.get("needs_database", False)
    database_type = state.get("database_type", "")
    
    if not needs_database:
        send_terminal_message(project_id, "ℹ️ No database needed. Skipping.\n\r", component_name)
        return {"database_deployed": False}
    
    config = HELM_CONFIGS.get(database_type)
    if not config:
        send_terminal_message(project_id, f"⚠️ Unknown database type: {database_type}. Skipping.\n\r", component_name)
        return {"database_deployed": False}
    
    release_name = f"{component_name}-db"
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
        
        # Write to gitops dir
        component_folder = component_name or "app"
        gitops_base = os.path.join(os.getcwd(), "temp", f"gitops_{project_id}")
        db_manifests_path = os.path.join(gitops_base, f"{component_folder}-db")
        os.makedirs(db_manifests_path, exist_ok=True)
        
        output_file = os.path.join(db_manifests_path, f"{database_type}.yaml")
        with open(output_file, "w") as f:
            f.write(rendered_yaml)
        
        send_terminal_message(project_id, f"✅ Database manifests generated: {component_folder}-db/{database_type}.yaml\n\r", component_name)
        
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
