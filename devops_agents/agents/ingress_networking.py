import os
from jinja2 import Environment, FileSystemLoader
from config.settings import settings
from app.kafka_terminal_producer import send_terminal_message


def generate_ingress(state):
    """
    Post-processing graph node: generates Ingress YAML.
    - Single project: uses ingress.j2 (single path rule)
    - Multi-project: uses ingress-multi.j2 (path-based routing)
    
    Writes to temp/gitops_{project_id}/ingress.yaml
    """
    project_id = state.get("project_id", "")
    is_multi_project = state.get("is_multi_project", False)
    components = state.get("components", [])
    
    namespace = project_id
    host = f"app-{project_id}.{settings.domain_name}"
    
    templates_dir = os.path.join(os.getcwd(), "templates", "k8s")
    env = Environment(loader=FileSystemLoader(templates_dir))
    
    gitops_base = os.path.join(os.getcwd(), "temp", f"gitops_{project_id}")
    os.makedirs(gitops_base, exist_ok=True)
    
    if is_multi_project:
        send_terminal_message(project_id, "🌐 Generating shared Ingress with path-based routing...\n\r")
        
        # Sort: specific paths first (/api, /auth), catch-all (/) last
        sorted_components = sorted(
            components,
            key=lambda c: (c.get("api_path_prefix", "/") == "/", c.get("api_path_prefix", "/"))
        )
        
        template_components = []
        for comp in sorted_components:
            template_components.append({
                "path_prefix": comp.get("api_path_prefix", "/"),
                "service_name": comp["app_name"],
            })
            send_terminal_message(project_id, f"   📍 {comp.get('api_path_prefix', '/')} → {comp['app_name']}\n\r")
        
        template = env.get_template("ingress-multi.j2")
        content = template.render(
            namespace=namespace,
            host=host,
            acm_certificate_arn=settings.acm_certificate_arn,
            components=template_components,
        )
    else:
        send_terminal_message(project_id, "🌐 Generating Ingress...\n\r")
        
        comp = components[0]
        template = env.get_template("ingress.j2")
        content = template.render(
            app_name=comp["app_name"],
            namespace=namespace,
            host=host,
            domain_name=settings.domain_name,
            acm_certificate_arn=settings.acm_certificate_arn,
        )
    
    ingress_path = os.path.join(gitops_base, "ingress.yaml")
    with open(ingress_path, "w") as f:
        f.write(content)
    
    send_terminal_message(project_id, f"✅ Ingress generated: {host}\n\r")
    return {}
