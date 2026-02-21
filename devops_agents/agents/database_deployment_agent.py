import os
import asyncio
from jinja2 import Environment, FileSystemLoader
import string
import secrets
from config.settings import settings
from app.kafka_terminal_producer import send_terminal_message


async def database_deployment_agent(state):
    """
    Database Manifest Generator Agent.
    Uses Jinja2 templates to render database YAML manifests.
    Dependency on Helm CLI is REMOVED.
    
    Paths:
      - Single project: temp/gitops_{project_id}/app/{database_type}.yaml
      - Multi-project:  temp/gitops_{project_id}/app/{component_name}/{database_type}.yaml
    
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
    
    # Map db type to template file
    template_map = {
        "mongodb": "mongodb.j2",
        "postgresql": "postgresql.j2",
        "mysql": "mysql.j2"
    }
    
    template_file = template_map.get(database_type)
    if not template_file:
        send_terminal_message(project_id, f"⚠️ Unknown database type: {database_type}. Skipping.\n\r", component_name)
        return {"database_deployed": False}
    
    # Determine release name and namespace
    if component_name:
        service_name = f"{component_name}-db-{database_type}"
    else:
        service_name = f"app-db-{database_type}"
    namespace = project_id
    
    send_terminal_message(project_id, f"📦 Generating {database_type} manifests via Jinja2...\n\r", component_name)
    
    # Process extracted Database Credentials, fallback to random secure passwords
    db_creds = state.get("database_credentials") or {}
    db_user = db_creds.get("db_user") or "admin"
    db_password = db_creds.get("db_password") or "".join(secrets.choice(string.ascii_letters + string.digits) for i in range(16))
    db_name = db_creds.get("db_name") or "appdb"
    db_root_password = db_creds.get("db_root_password") or "".join(secrets.choice(string.ascii_letters + string.digits) for i in range(16))

    try:
        # Use absolute path to templates to avoid CWD issues
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        templates_dir = os.path.join(base_dir, "templates", "k8s")
        env = Environment(loader=FileSystemLoader(templates_dir))
        
        template = env.get_template(template_file)
        content = template.render(
            service_name=service_name,
            namespace=namespace,
            db_user=db_user,
            db_password=db_password,
            db_name=db_name,
            db_root_password=db_root_password
        )
        
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
            f.write(content)
        
        label = f"{component_name}/{database_type}.yaml" if component_name else f"{database_type}.yaml"
        send_terminal_message(project_id, f"✅ Database manifests generated: {label}\n\r", component_name)
        
        return {
            "database_deployed": True,
            "database_service_name": service_name,
        }
        
    except Exception as e:
        send_terminal_message(project_id, f"❌ Database manifest generation failed: {str(e)}\n\r", component_name)
        return {"database_deployed": False}
