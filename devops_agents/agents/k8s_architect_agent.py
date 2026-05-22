import os
from jinja2 import Environment, FileSystemLoader
from config.settings import settings
from app.kafka_terminal_producer import send_terminal_message


async def k8s_architect_agent(state):
    """
    K8s Architect Agent — pure manifest generation.
    Generates Deployment + Service YAML only. No kubectl, no AWS calls.
    
        Paths:
            - temp/gitops_{project_id}/app/{app_name}/
    
    ECR pull secret, Ingress, GitOps push, ArgoCD → post-processing graph.
    """
    project_id = state.get("project_id", "")
    component = state.get("component") or {}
    component_name = component.get("name")
    
    if not component:
        send_terminal_message(project_id, "❌ Missing component details. Skipping K8s Architect.\n\r", component_name)
        return {"build_status": "k8s_failed_no_component"}
        
    if not state.get("image_url"):
        send_terminal_message(project_id, "❌ No image URL found. Pipeline agent failed to provide image.\n\r", component_name)
        return {"build_status": "k8s_failed_no_image"}

    send_terminal_message(project_id, "👷 Generating K8s manifests...\n\r", component_name)

    # Build app name
    app_name = component_name or "app"
    namespace = project_id

    env_list = component.get("env_variables", []) if component else []
    env_vars = {env.get("key"): str(env.get("value", "")) for env in env_list if env.get("key")}

    resources = component.get("resources", {}) if component else {}

    port = component.get("port")
    health_path = component.get("health_check_path", "/")

    # Template data
    data = {
        "app_name": app_name,
        "namespace": namespace,
        "replicas": 1,
        "image_url": state.get("image_url"),
        "port": port or 3000,
        "memory_request": resources.get("memory_request", "512Mi"),
        "cpu_request": resources.get("cpu_request", "200m"),
        "memory_limit": resources.get("memory_limit", "768Mi"),
        "cpu_limit": resources.get("cpu_limit", "1000m"),
        "health_check_path": health_path or "/",
        "image_pull_secret": "regcred",
        "domain_name": settings.domain_name,
        "acm_certificate_arn": settings.acm_certificate_arn,
        "env_vars": env_vars or {},
    }

    # Generate Deployment + Service YAML
    # Use absolute path to templates to avoid CWD issues in parallel execution
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    templates_dir = os.path.join(base_dir, "templates", "k8s")
    env = Environment(loader=FileSystemLoader(templates_dir))
    
    gitops_base = state.get("gitops_dir")
    manifests_path = os.path.join(gitops_base, "app", app_name)
    os.makedirs(manifests_path, exist_ok=True)
    
    for template_file in ["deployment.j2", "service.j2"]:
        template = env.get_template(template_file)
        content = template.render(data)
        
        output_filename = template_file.replace(".j2", ".yaml")
        output_path = os.path.join(manifests_path, output_filename)
        
        with open(output_path, "w") as f:
            f.write(content)
        
        label = f"{component_name}/{output_filename}" if component_name else output_filename
        send_terminal_message(project_id, f"📄 Generated {label}\n\r", component_name)
    
    send_terminal_message(project_id, "✅ K8s manifests ready.\n\r", component_name)
    
    return {
        "k8s_status": "manifests_ready",
        "k8s_app_name": app_name,
        "k8s_port": data["port"],
    }
