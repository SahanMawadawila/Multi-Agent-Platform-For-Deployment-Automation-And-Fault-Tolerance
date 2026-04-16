import os
from jinja2 import Environment, FileSystemLoader
from config.settings import settings
from app.kafka_terminal_producer import send_terminal_message


async def k8s_architect_agent(state):
    """
    K8s Architect Agent — pure manifest generation.
    Generates Deployment + Service YAML only. No kubectl, no AWS calls.
    
    Paths:
      - Single project: temp/gitops_{project_id}/app/
      - Multi-project:  temp/gitops_{project_id}/app/{component_name}/
    
    ECR pull secret, Ingress, GitOps push, ArgoCD → post-processing graph.
    """
    project_id = state.get("project_id", "")
    analysis = state.get("analyzed_repository_details")
    component_spec = state.get("component_spec") or {}
    component_name = state.get("component_name")
    is_multi_project = state.get("is_multi_project", False)
    overridden_envs = state.get("overridden_envs", {})
    
    if not analysis and not component_spec:
        send_terminal_message(project_id, "❌ Missing component details. Skipping K8s Architect.\n\r", component_name)
        return {"build_status": "k8s_failed_no_component_spec"}
        
    if not state.get("image_url"):
        send_terminal_message(project_id, "❌ No image URL found. Pipeline agent failed to provide image.\n\r", component_name)
        return {"build_status": "k8s_failed_no_image"}

    send_terminal_message(project_id, "👷 Generating K8s manifests...\n\r", component_name)

    # Build app name
    app_name = f"app-{project_id}-{component_name}" if component_name else f"app-{project_id}"
    namespace = project_id

    env_list = component_spec.get("env_variables", []) if component_spec else []
    env_vars = {env.get("key"): str(env.get("value", "")) for env in env_list if env.get("key")}

    resources = component_spec.get("resources", {}) if component_spec else {}

    port = component_spec.get("port") if component_spec else getattr(analysis, "port", None)
    health_path = component_spec.get("health_check_path") if component_spec else getattr(analysis, "health_check_path", "/")
    if port is None and analysis:
        port = analysis.port

    # Template data
    data = {
        "app_name": app_name,
        "namespace": namespace,
        "replicas": 1,
        "image_url": state.get("image_url"),
        "port": port or 3000,
        "memory_limit": resources.get("memory_limit") or getattr(analysis, "memory_limit", "256Mi"),
        "cpu_limit": resources.get("cpu_limit") or getattr(analysis, "cpu_limit", "200m"),
        "health_check_path": health_path or "/",
        "image_pull_secret": "regcred",
        "domain_name": settings.domain_name,
        "acm_certificate_arn": settings.acm_certificate_arn,
        "env_vars": overridden_envs or env_vars or {},
    }

    # Generate Deployment + Service YAML
    # Use absolute path to templates to avoid CWD issues in parallel execution
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    templates_dir = os.path.join(base_dir, "templates", "k8s")
    env = Environment(loader=FileSystemLoader(templates_dir))
    
    # Determine output path:
    #   Single:  temp/gitops_{project_id}/app/
    #   Multi:   temp/gitops_{project_id}/app/{component_name}/
    gitops_base = os.path.join(os.getcwd(), "temp", f"gitops_{project_id}")
    if is_multi_project and component_name:
        manifests_path = os.path.join(gitops_base, "app", component_name)
    else:
        manifests_path = os.path.join(gitops_base, "app")
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
