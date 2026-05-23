import os
from jinja2 import Environment, FileSystemLoader
from config.settings import settings
from app.kafka_terminal_producer import send_terminal_message


def generate_ingress(state):
    """
    Post-processing graph node: generates Ingress YAML.
    - Single project: uses ingress.j2 (single path rule)
    - Multi-project: uses ingress-multi.j2 (path-based routing)
    
    Writes to: temp/gitops_{project_id}/app/ingress.yaml
    """
    project_id = state.get("project_id", "")
    components = state.get("components", [])
    ingress_config = state.get("ingress_config") or {}
    
    namespace = project_id
    host = ingress_config.get("host") or f"app-{project_id}.{settings.domain_name}"
    
    # Use absolute path to templates
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    templates_dir = os.path.join(base_dir, "templates", "k8s")
    env = Environment(loader=FileSystemLoader(templates_dir))
    
    # Ingress always goes to app/ingress.yaml
    gitops_base = state.get("gitops_dir")
    app_dir = os.path.join(gitops_base, "app")
    os.makedirs(app_dir, exist_ok=True)
    
    exposed_components = [
        comp for comp in components
        if (comp.get("ingress") or {}).get("expose", True)
    ]
    is_multi_project = len(exposed_components) > 1

    if ingress_config.get("rules"):
        send_terminal_message(project_id, "🌐 Generating Ingress from plan rules...\n\r")

        service_map = {comp.get("name"): comp.get("name") for comp in components}
        template_components = []
        for rule in ingress_config.get("rules", []):
            target_service = service_map.get(rule.get("service")) or rule.get("service")
            port = 80
            for comp in components:
                if comp.get("name") == rule.get("service"):
                    port = comp.get("container_port", 80)
                    break
            
            template_components.append({
                "path_prefix": rule.get("path", "/"),
                "service_name": target_service,
                "port": port,
            })

        template = env.get_template("ingress-multi.j2")
        content = template.render(
            namespace=namespace,
            host=host,
            acm_certificate_arn=settings.acm_certificate_arn,
            components=template_components,
        )
    elif is_multi_project:
        send_terminal_message(project_id, "🌐 Generating shared Ingress with path-based routing...\n\r")
        
        # Sort: specific paths first (/api, /auth), catch-all (/) last
        sorted_components = sorted(
            exposed_components,
            key=lambda c: (
                (c.get("ingress") or {}).get("path_prefix", "/") == "/",
                (c.get("ingress") or {}).get("path_prefix", "/"),
            )
        )
        
        template_components = []
        for comp in sorted_components:
            ingress = comp.get("ingress") or {}
            template_components.append({
                "path_prefix": ingress.get("path_prefix", "/"),
                "service_name": comp.get("name"),
                "port": comp.get("container_port", 80),
            })
            send_terminal_message(
                project_id,
                f"   📍 {ingress.get('path_prefix', '/')} → {comp.get('name')}\n\r",
            )
        
        template = env.get_template("ingress-multi.j2")
        content = template.render(
            namespace=namespace,
            host=host,
            acm_certificate_arn=settings.acm_certificate_arn,
            components=template_components,
        )
    else:
        if not exposed_components:
            send_terminal_message(project_id, "ℹ️ No application components to expose. Skipping ingress.\n\r")
            return {}
        send_terminal_message(project_id, "🌐 Generating Ingress...\n\r")
        
        comp = exposed_components[0]
        app_name = comp.get("name")
        template = env.get_template("ingress.j2")
        content = template.render(
            app_name=app_name,
            namespace=namespace,
            host=host,
            domain_name=settings.domain_name,
            acm_certificate_arn=settings.acm_certificate_arn,
            port=comp.get("container_port", 80),
        )
    
    ingress_path = os.path.join(app_dir, "ingress.yaml")
    with open(ingress_path, "w") as f:
        f.write(content)
    
    send_terminal_message(project_id, f"✅ Ingress generated: {host}\n\r")
    return {}
