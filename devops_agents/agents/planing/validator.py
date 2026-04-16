"""Validator to reconcile components and connections without inventing infra."""

from typing import List, Tuple, Optional
from urllib.parse import urlparse, urlunparse

from agents.plan_schemas import (
    ApplicationComponent,
    InfrastructureComponent,
    Connection,
    DeploymentPlan,
    IngressConfig,
    IngressRule,
    EnvVariable,
)


DB_PROTOCOLS = {
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "mysql": "mysql",
    "mongodb": "mongodb",
    "mongo": "mongodb",
}

DB_IMAGE_MAP = {
    "postgresql": "postgres:latest",
    "mysql": "mysql:latest",
    "mongodb": "mongo:latest",
}

DB_PORT_MAP = {
    "postgresql": 5432,
    "mysql": 3306,
    "mongodb": 27017,
}


def _normalize_db_type(value: str) -> Optional[str]:
    if not value:
        return None
    lowered = value.lower()
    for key, normalized in DB_PROTOCOLS.items():
        if key in lowered:
            return normalized
    return None


def _build_db_service_name(component_name: Optional[str], db_type: str) -> str:
    if component_name:
        return f"{component_name}-db-{db_type}"
    return f"app-db-{db_type}"


def _replace_db_host_in_url(url: str, service_name: str) -> str:
    if not url:
        return service_name

    try:
        parsed = urlparse(url)
        if parsed.scheme and parsed.netloc:
            netloc = parsed.netloc
            userinfo = ""
            hostport = netloc
            if "@" in netloc:
                userinfo, hostport = netloc.rsplit("@", 1)
            host = hostport
            port = ""
            if ":" in hostport:
                host, port = hostport.split(":", 1)
            new_hostport = f"{service_name}:{port}" if port else service_name
            new_netloc = f"{userinfo}@{new_hostport}" if userinfo else new_hostport
            return urlunparse(parsed._replace(netloc=new_netloc))
    except Exception:
        return url.replace("localhost", service_name).replace("127.0.0.1", service_name)

    return url.replace("localhost", service_name).replace("127.0.0.1", service_name)


def _update_component_env(
    app_components: List[ApplicationComponent],
    component_name: str,
    env_key: str,
    resolved_value: str,
):
    if not env_key or not resolved_value:
        return

    for component in app_components:
        if component.name != component_name:
            continue
        for env_var in component.env_variables:
            if env_var.key == env_key:
                env_var.value = resolved_value
                env_var.source = "auto_generate"
                return
        component.env_variables.append(
            EnvVariable(
                key=env_key,
                value=resolved_value,
                source="auto_generate",
                editable=True,
                sensitive=False,
            )
        )
        return


def build_ingress(app_components: List[ApplicationComponent], project_id: str) -> IngressConfig:
    rules = []
    for component in app_components:
        if not component.ingress.expose:
            continue
        rules.append(IngressRule(
            path=component.ingress.path_prefix,
            service=component.name,
            port=component.port,
        ))

    rules.sort(key=lambda rule: (rule.path == "/", rule.path))

    return IngressConfig(
        host=f"app-{project_id}.flowpilotai.me",
        tls=True,
        rules=rules,
    )


def reconcile_plan(
    app_components: List[ApplicationComponent],
    infra_components: List[InfrastructureComponent],
    connections: List[Connection],
    project_id: str,
    logger,
) -> DeploymentPlan:
    component_names = {component.name for component in [*app_components, *infra_components]}
    app_component_names = {component.name for component in app_components}
    single_app_name = app_components[0].name if len(app_components) == 1 else None

    for connection in connections:
        if connection.from_component not in app_component_names and single_app_name:
            connection.from_component = single_app_name

        db_type = _normalize_db_type(connection.protocol) or _normalize_db_type(connection.to_component)
        if db_type:
            service_name = _build_db_service_name(
                connection.from_component if connection.from_component in app_component_names else single_app_name,
                db_type,
            )
            connection.scope = "internal"
            connection.to_component = service_name
            connection.resolved_value = _replace_db_host_in_url(connection.resolved_value, service_name)
            _update_component_env(app_components, connection.from_component, connection.env_key, connection.resolved_value)

            if service_name not in component_names:
                infra_components.append(
                    InfrastructureComponent(
                        name=service_name,
                        category="database",
                        image=DB_IMAGE_MAP[db_type],
                        port=DB_PORT_MAP[db_type],
                    )
                )
                component_names.add(service_name)

        if connection.scope == "internal" and connection.to_component not in component_names:
            logger.warning(
                "Missing infrastructure/component for internal connection: %s -> %s",
                connection.from_component,
                connection.to_component,
            )

    is_monorepo = len(app_components) > 1 or len({component.path for component in app_components}) > 1
    ingress = build_ingress(app_components, project_id)

    return DeploymentPlan(
        is_monorepo=is_monorepo,
        components=[*app_components, *infra_components],
        connections=connections,
        ingress=ingress,
    )
