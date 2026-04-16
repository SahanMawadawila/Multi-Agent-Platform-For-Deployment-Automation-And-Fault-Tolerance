import os
from jinja2 import Environment, FileSystemLoader
from app.kafka_terminal_producer import send_terminal_message


def _resolve_mount_path(image: str, name: str) -> str:
    target = f"{image} {name}".lower()
    if "postgres" in target:
        return "/var/lib/postgresql/data"
    if "mysql" in target or "mariadb" in target:
        return "/var/lib/mysql"
    if "mongo" in target:
        return "/data/db"
    if "redis" in target:
        return "/data"
    return "/data"


def _collect_env_vars(component: dict) -> dict:
    env_vars = {}

    for env in component.get("env_variables", []) or []:
        key = env.get("key")
        if not key:
            continue
        env_vars[key] = str(env.get("value", ""))

    credentials = component.get("credentials", {}) or {}
    for key, cred in credentials.items():
        if not key:
            continue
        if isinstance(cred, dict):
            env_vars[key] = str(cred.get("value", ""))
        else:
            env_vars[key] = str(cred)

    return env_vars


async def infra_deployment_agent(state: dict):
    """
    Generates K8s manifests for infrastructure components only.
    Outputs into temp/gitops_{project_id}/app/infra/{service_name}/
    """
    project_id = state.get("project_id", "")
    component = state.get("infra_component") or {}
    service_name = component.get("name")

    if not service_name:
        send_terminal_message(project_id, "❌ Missing infrastructure component name. Skipping.\n\r")
        return {"infra_status": "infra_failed_missing_name"}

    image = component.get("image")
    port = component.get("port")

    if not image or not port:
        send_terminal_message(project_id, f"❌ Missing image/port for {service_name}. Skipping.\n\r")
        return {"infra_status": "infra_failed_missing_image_or_port"}

    send_terminal_message(project_id, f"🧱 Generating infra manifests for {service_name}...\n\r")

    resources = component.get("resources", {}) or {}
    storage = component.get("storage") or {}

    storage_size = storage.get("size")
    storage_class = storage.get("storage_class", "gp2")
    stateful = bool(storage_size) or component.get("category") == "database"

    data = {
        "service_name": service_name,
        "namespace": project_id,
        "replicas": resources.get("replicas", 1),
        "image": image,
        "port": port,
        "env_vars": _collect_env_vars(component),
        "memory_limit": resources.get("memory_limit", "256Mi"),
        "cpu_limit": resources.get("cpu_limit", "200m"),
        "storage_size": storage_size,
        "storage_class": storage_class,
        "stateful": stateful,
        "mount_path": _resolve_mount_path(image, service_name) if stateful else "",
    }

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    templates_dir = os.path.join(base_dir, "templates", "k8s")
    env = Environment(loader=FileSystemLoader(templates_dir))

    gitops_base = os.path.join(os.getcwd(), "temp", f"gitops_{project_id}")
    manifests_path = os.path.join(gitops_base, "app", "infra", service_name)
    os.makedirs(manifests_path, exist_ok=True)

    for template_file in ["infra-deployment.j2", "infra-service.j2"]:
        template = env.get_template(template_file)
        content = template.render(data)

        output_filename = template_file.replace(".j2", ".yaml")
        output_path = os.path.join(manifests_path, output_filename)
        with open(output_path, "w") as f:
            f.write(content)

        send_terminal_message(project_id, f"📄 Generated infra/{service_name}/{output_filename}\n\r")

    send_terminal_message(project_id, f"✅ Infra manifests ready for {service_name}.\n\r")

    return {"infra_status": "manifests_ready"}
