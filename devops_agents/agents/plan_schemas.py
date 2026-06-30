"""
Deployment Plan Schemas
Pydantic models defining the full deployment plan structure.
Used as:
  1. LLM structured output (DeploymentPlan is bound as a tool)
  2. Validation for plan JSON
  3. Serialization for Kafka/WebSocket delivery
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Any, List, Optional, Dict, Literal, Union
from datetime import datetime


# ---------------------------------------------------------------------------
# Helpers – coerce common LLM output quirks
# ---------------------------------------------------------------------------

def _coerce_int(v: Any) -> int:
    """LLMs sometimes return numeric values as strings (e.g., '3000')."""
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        try:
            return int(v)
        except ValueError:
            pass
    if isinstance(v, float):
        return int(v)
    return v  # let Pydantic raise its own error


def _coerce_bool(v: Any) -> bool:
    """LLMs sometimes return booleans as strings ('true'/'false')."""
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        if v.lower() in ("true", "1", "yes"):
            return True
        if v.lower() in ("false", "0", "no"):
            return False
    return v  # let Pydantic raise its own error


def _coerce_env_item(item: Any) -> Any:
    """Coerce a single env variable item that the LLM may have flattened.

    Common LLM mistakes:
      - Returns a plain string like "PORT=3000" -> split into key/value
      - Returns a flat dict {"PORT": "3000"} -> wrap into EnvVariable shape
      - Returns a dict with only key/value but missing source/editable/sensitive -> fine, Pydantic defaults handle it
    """
    if isinstance(item, str):
        # e.g. "PORT=3000" or just "PORT"
        if "=" in item:
            k, _, v = item.partition("=")
            return {"key": k.strip(), "value": v.strip(), "source": "detected"}
        return {"key": item.strip(), "value": "", "source": "detected"}
    if isinstance(item, dict) and "key" not in item:
        # Flat dict like {"PORT": "3000"} - take the first key/value pair
        for k, v in item.items():
            return {"key": str(k), "value": str(v) if v is not None else "", "source": "detected"}
        return item  # empty dict, let Pydantic handle
    return item  # already a proper dict or EnvVariable



class EnvVariable(BaseModel):
    """An environment variable detected or configured for a component."""
    key: str = Field(..., description="Environment variable name")
    value: str = Field("", description="Environment variable value")
    source: Literal["detected", "override", "auto_generate", "default"] = Field(
        "detected", description="How this value was determined"
    )
    editable: bool = Field(True, description="Whether the user can edit this value")
    sensitive: bool = Field(False, description="Whether this is a secret/password")

    @field_validator('value', mode='before')
    @classmethod
    def coerce_value_to_str(cls, v):
        """LLM might return int/float/bool for env values; always stringify."""
        if v is None:
            return ""
        return str(v)

    @field_validator('editable', mode='before')
    @classmethod
    def coerce_editable(cls, v):
        return _coerce_bool(v) if v is not None else True

    @field_validator('sensitive', mode='before')
    @classmethod
    def coerce_sensitive(cls, v):
        return _coerce_bool(v) if v is not None else False

    @field_validator('source', mode='before')
    @classmethod
    def coerce_source(cls, v):
        """Normalise unknown source values to 'detected'."""
        allowed = {"detected", "override", "auto_generate", "default"}
        if isinstance(v, str) and v not in allowed:
            return "detected"
        return v if v is not None else "detected"


class CredentialField(BaseModel):
    """A single credential field for infrastructure components."""
    value: str = Field("", description="Credential value (empty if auto_generate)")
    source: Literal["detected", "auto_generate"] = Field(
        "auto_generate", description="How this value was determined"
    )
    editable: bool = Field(True, description="Whether the user can edit this value")
    sensitive: bool = Field(True, description="Whether this is a secret")

    @field_validator('value', mode='before')
    @classmethod
    def coerce_value_to_str(cls, v):
        if v is None:
            return ""
        return str(v)

    @field_validator('source', mode='before')
    @classmethod
    def coerce_source(cls, v):
        allowed = {"detected", "auto_generate"}
        if isinstance(v, str) and v not in allowed:
            return "auto_generate"
        return v if v is not None else "auto_generate"

    @field_validator('editable', mode='before')
    @classmethod
    def coerce_editable(cls, v):
        return _coerce_bool(v) if v is not None else True

    @field_validator('sensitive', mode='before')
    @classmethod
    def coerce_sensitive(cls, v):
        return _coerce_bool(v) if v is not None else True

class ResourceSpec(BaseModel):
    """Resource requests/limits for a Kubernetes deployment."""
    cpu_request: str = Field("200m", description="CPU request (e.g., '100m', '200m', '500m')")
    memory_request: str = Field("512Mi", description="Memory request (e.g., '256Mi', '512Mi', '1Gi')")
    cpu_limit: str = Field("500m", description="CPU limit (e.g., '200m', '500m', '1')")
    memory_limit: str = Field("512Mi", description="Memory limit (e.g., '256Mi', '512Mi', '1Gi')")
    replicas: int = Field(1, description="Number of pod replicas")

    @field_validator('cpu_request', 'memory_request', 'cpu_limit', 'memory_limit', mode='before')
    @classmethod
    def coerce_str(cls, v):
        if v is None:
            return "200m"  # safe default
        return str(v)

    @field_validator('replicas', mode='before')
    @classmethod
    def coerce_replicas(cls, v):
        if v is None:
            return 1
        return _coerce_int(v)


class StorageSpec(BaseModel):
    """Persistent storage configuration."""
    size: str = Field("1Gi", description="Storage size (e.g., '1Gi', '5Gi')")
    storage_class: str = Field("gp2", description="Kubernetes storage class")

    @model_validator(mode='before')
    @classmethod
    def coerce_from_string(cls, data):
        """LLM might return just a size string like '5Gi' instead of the full dict."""
        if isinstance(data, str):
            return {"size": data, "storage_class": "gp2"}
        if data is None:
            return {"size": "1Gi", "storage_class": "gp2"}
        return data


class IngressSpec(BaseModel):
    """Ingress configuration for a component."""
    path_prefix: str = Field("/", description="URL path prefix for routing (e.g., '/', '/api')")
    expose: bool = Field(True, description="Whether to expose this component via ingress")

    @model_validator(mode='before')
    @classmethod
    def coerce_from_string(cls, data):
        """LLM might return just a path string like '/api' instead of the full dict."""
        if isinstance(data, str):
            return {"path_prefix": data, "expose": True}
        if data is None:
            return {"path_prefix": "/", "expose": True}
        return data

    @field_validator('expose', mode='before')
    @classmethod
    def coerce_expose(cls, v):
        return _coerce_bool(v) if v is not None else True


class ApplicationComponent(BaseModel):
    """A buildable application component (goes through Dockerfile → CI/CD → ECR → K8s)."""
    name: str = Field(..., description="Component name. Use 'app' for single-app projects.")
    type: Literal["application"] = Field("application", description="Component type")
    path: str = Field(".", description="Path relative to repo root (e.g., '.', 'backend', 'services/auth')")
    project_type: str = Field(..., description="Project type: 'node', 'springboot', 'python'")
    framework: Optional[str] = Field(None, description="Detected framework: next, nest, express, spring-boot, django, fastapi")
    version: str = Field(..., description="Runtime version (e.g., '18' for Node, '17' for Java, '3.11' for Python)")
    package_manager: str = Field(..., description="Package manager: npm, yarn, pnpm, maven, gradle, pip")
    role: str = Field("backend", description="Component role: 'frontend', 'backend', 'worker', 'api-gateway'")
    port: int = Field(..., description="Application port (e.g., 3000, 8080)")
    build_image: bool = Field(True, description="Whether to build a Docker image (always true for application)")
    image_name: str = Field(..., description="ECR image name (e.g., '{project_id}-backend')")
    health_check_path: str = Field("/", description="Path for K8s liveness/readiness probes")
    needs_build_step: bool = Field(False, description="Whether a build step is needed (TypeScript, Next.js, etc.)")
    build_command: str = Field("", description="Build command (e.g., 'npm run build')")
    run_command: str = Field(..., description="Start command (e.g., 'npm start', 'node dist/main.js')")
    resources: ResourceSpec = Field(default_factory=ResourceSpec)
    env_variables: List[EnvVariable] = Field(default_factory=list, description="Environment variables for this component")
    ingress: IngressSpec = Field(default_factory=IngressSpec)

    @field_validator('port', mode='before')
    @classmethod
    def coerce_port(cls, v):
        return _coerce_int(v)

    @field_validator('build_image', 'needs_build_step', mode='before')
    @classmethod
    def coerce_bools(cls, v):
        return _coerce_bool(v) if v is not None else True

    @field_validator('version', mode='before')
    @classmethod
    def coerce_version(cls, v):
        """LLM may return version as int/float (e.g., 18 instead of '18')."""
        if v is None:
            return ""
        return str(v)

    @field_validator('build_command', 'run_command', 'image_name', mode='before')
    @classmethod
    def coerce_str_fields(cls, v):
        if v is None:
            return ""
        return str(v)

    @field_validator('resources', mode='before')
    @classmethod
    def default_resources(cls, v):
        return v if v is not None else {}

    @field_validator('env_variables', mode='before')
    @classmethod
    def default_env(cls, v):
        if v is None:
            return []
        if isinstance(v, list):
            return [_coerce_env_item(item) for item in v]
        return v

    @field_validator('ingress', mode='before')
    @classmethod
    def default_ingress(cls, v):
        return v if v is not None else {}


class InfrastructureComponent(BaseModel):
    """A pre-built infrastructure component (uses Docker Hub image, only K8s manifests needed)."""
    name: str = Field(..., description="Service name (e.g., 'mongodb', 'kafka', 'redis')")
    type: Literal["infrastructure"] = Field("infrastructure", description="Component type")
    scope: Literal["project", "global"] = Field("project", description="Scope of the infrastructure service")
    owner_app: Optional[str] = Field(None, description="Owning app name if scope is 'project'")
    category: str = Field(..., description="Infrastructure category: 'database', 'message_broker', 'cache', 'coordination', 'search'")
    image: str = Field(..., description="Full Docker image with tag (e.g., 'mongo:7.0', 'confluentinc/cp-kafka:7.6.0')")
    build_image: bool = Field(False, description="Whether to build a Docker image (always false for infrastructure)")
    port: int = Field(..., description="Primary service port")
    credentials: Dict[str, CredentialField] = Field(default_factory=dict, description="Credentials (e.g., db_user, db_password)")
    env_variables: List[EnvVariable] = Field(default_factory=list, description="Additional env vars for this service")
    storage: Optional[StorageSpec] = Field(default_factory=StorageSpec, description="Persistent storage config")
    resources: ResourceSpec = Field(default_factory=ResourceSpec)
    manifest_yaml: Optional[str] = Field(
        None,
        description="Optional any snippet of yaml manifest found in the codebase for this infrastructure component"
    )
    template_key: Optional[str] = Field(
        None,
        description="Registry template key (e.g., 'postgresql', 'kafka'). None = custom/unsupported, uses LLM fallback."
    )
    version_warning: Optional[str] = Field(
        None,
        description="Warning about version compatibility shown during plan review (e.g., 'Your code uses Spring Kafka 2.x which is best compatible with Kafka 7.4.0')"
    )
    supported_versions: Optional[List[str]] = Field(
        None,
        description="List of tested image versions from the registry (e.g., ['16-alpine', '15-alpine', '14-alpine'] for PostgreSQL)"
    )

    @field_validator('resources', mode='before')
    @classmethod
    def default_resources(cls, v):
        return v if v is not None else {}

    @field_validator('port', mode='before')
    @classmethod
    def coerce_port(cls, v):
        return _coerce_int(v)

    @field_validator('build_image', mode='before')
    @classmethod
    def coerce_build_image(cls, v):
        return _coerce_bool(v) if v is not None else False

    @field_validator('storage', mode='before')
    @classmethod
    def coerce_storage(cls, v):
        """LLM might send a string like '5Gi' or null."""
        if v is None:
            return None
        if isinstance(v, str):
            return {"size": v, "storage_class": "gp2"}
        return v

    @field_validator('env_variables', mode='before')
    @classmethod
    def default_env(cls, v):
        if v is None:
            return []
        if isinstance(v, list):
            return [_coerce_env_item(item) for item in v]
        return v

    @field_validator('credentials', mode='before')
    @classmethod
    def default_creds(cls, v):
        if v is None:
            return {}
        if isinstance(v, dict):
            coerced = {}
            for key, val in v.items():
                if isinstance(val, str):
                    # LLM returned a plain string instead of a CredentialField dict – wrap it
                    coerced[key] = {
                        "value": val,
                        "source": "detected",
                        "editable": True,
                        "sensitive": True,
                    }
                else:
                    coerced[key] = val
            return coerced
        return v


class Connection(BaseModel):
    """A connection between two components or to an external service."""
    from_component: str = Field(..., description="Source component name (e.g., 'backend')")
    to_component: str = Field(..., description="Target component or external service name (e.g., 'mongodb', 'Stripe API')")
    scope: Literal["internal", "external"] = Field(..., description="'internal' = deployed in cluster, 'external' = third-party service")
    env_updates: List[EnvVariable] = Field(
        default_factory=list,
        description="All env variables updated for this connection",
    )

    @field_validator('scope', mode='before')
    @classmethod
    def coerce_scope(cls, v):
        allowed = {"internal", "external"}
        if isinstance(v, str) and v.lower() not in allowed:
            return "internal"
        return v.lower() if isinstance(v, str) else v

    @field_validator('env_updates', mode='before')
    @classmethod
    def coerce_env_updates(cls, v):
        if v is None:
            return []
        if isinstance(v, list):
            return [_coerce_env_item(item) for item in v]
        return v


class EnvCorrection(BaseModel):
    """A single env variable correction identified by the plan reviewer."""
    component_name: str = Field(..., description="Name of the component whose env variable needs correction")
    key: str = Field(..., description="Env variable key to correct")
    corrected_value: str = Field(..., description="The corrected value for Kubernetes deployment")
    reason: str = Field("", description="Brief reason for this correction")

    @field_validator('corrected_value', mode='before')
    @classmethod
    def coerce_value_to_str(cls, v):
        if v is None:
            return ""
        return str(v)


class IngressRule(BaseModel):
    """A single ingress routing rule."""
    path: str = Field(..., description="URL path (e.g., '/', '/api')")
    service: str = Field(..., description="Target service name")
    port: int = Field(..., description="Target service port")

    @field_validator('port', mode='before')
    @classmethod
    def coerce_port(cls, v):
        return _coerce_int(v)


class IngressConfig(BaseModel):
    """Global ingress configuration."""
    host: str = Field(..., description="Hostname for the ingress (e.g., 'app-{project_id}.flowpilotai.me')")
    tls: bool = Field(True, description="Whether to enable TLS/HTTPS")
    rules: List[IngressRule] = Field(default_factory=list, description="Routing rules")

    @field_validator('tls', mode='before')
    @classmethod
    def coerce_tls(cls, v):
        return _coerce_bool(v) if v is not None else True

    @field_validator('rules', mode='before')
    @classmethod
    def default_rules(cls, v):
        return v if v is not None else []


class DeploymentPlan(BaseModel):
    """
    Complete deployment plan for a project.
    This is the top-level schema returned by the planning agent.
    """
    components: List[Union[ApplicationComponent, InfrastructureComponent]] = Field(
        ..., description="All components to deploy (applications + infrastructure)"
    )
    connections: List[Connection] = Field(
        default_factory=list, description="All connections between components and external services"
    )
    ingress: IngressConfig = Field(..., description="Ingress routing configuration")
