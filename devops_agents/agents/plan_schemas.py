"""
Deployment Plan Schemas
Pydantic models defining the full deployment plan structure.
Used as:
  1. LLM structured output (DeploymentPlan is bound as a tool)
  2. Validation for plan JSON
  3. Serialization for Kafka/WebSocket delivery
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Literal, Union
from datetime import datetime


class EnvVariable(BaseModel):
    """An environment variable detected or configured for a component."""
    key: str = Field(..., description="Environment variable name")
    value: str = Field("", description="Environment variable value")
    source: Literal["detected", "override", "auto_generate", "default"] = Field(
        "detected", description="How this value was determined"
    )
    editable: bool = Field(True, description="Whether the user can edit this value")
    sensitive: bool = Field(False, description="Whether this is a secret/password")


class CredentialField(BaseModel):
    """A single credential field for infrastructure components."""
    value: str = Field("", description="Credential value (empty if auto_generate)")
    source: Literal["detected", "auto_generate"] = Field(
        "auto_generate", description="How this value was determined"
    )
    editable: bool = Field(True, description="Whether the user can edit this value")
    sensitive: bool = Field(True, description="Whether this is a secret")


class ResourceSpec(BaseModel):
    """Resource limits for a Kubernetes deployment."""
    cpu_limit: str = Field("200m", description="CPU limit (e.g., '200m', '500m', '1')")
    memory_limit: str = Field("256Mi", description="Memory limit (e.g., '256Mi', '512Mi', '1Gi')")
    replicas: int = Field(1, description="Number of pod replicas")


class StorageSpec(BaseModel):
    """Persistent storage configuration."""
    size: str = Field("1Gi", description="Storage size (e.g., '1Gi', '5Gi')")
    storage_class: str = Field("gp2", description="Kubernetes storage class")


class IngressSpec(BaseModel):
    """Ingress configuration for a component."""
    path_prefix: str = Field("/", description="URL path prefix for routing (e.g., '/', '/api')")
    expose: bool = Field(True, description="Whether to expose this component via ingress")


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

    @field_validator('resources', mode='before')
    @classmethod
    def default_resources(cls, v):
        return v if v is not None else {}

    @field_validator('env_variables', mode='before')
    @classmethod
    def default_env(cls, v):
        return v if v is not None else []

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

    @field_validator('resources', mode='before')
    @classmethod
    def default_resources(cls, v):
        return v if v is not None else {}

    @field_validator('env_variables', mode='before')
    @classmethod
    def default_env(cls, v):
        return v if v is not None else []

    @field_validator('credentials', mode='before')
    @classmethod
    def default_creds(cls, v):
        return v if v is not None else {}


class Connection(BaseModel):
    """A connection between two components or to an external service."""
    from_component: str = Field(..., description="Source component name (e.g., 'backend')")
    to_component: str = Field(..., description="Target component or external service name (e.g., 'mongodb', 'Stripe API')")
    scope: Literal["internal", "external"] = Field(..., description="'internal' = deployed in cluster, 'external' = third-party service")
    env_updates: List[EnvVariable] = Field(
        default_factory=list,
        description="All env variables updated for this connection",
    )


class IngressRule(BaseModel):
    """A single ingress routing rule."""
    path: str = Field(..., description="URL path (e.g., '/', '/api')")
    service: str = Field(..., description="Target service name")
    port: int = Field(..., description="Target service port")


class IngressConfig(BaseModel):
    """Global ingress configuration."""
    host: str = Field(..., description="Hostname for the ingress (e.g., 'app-{project_id}.flowpilotai.me')")
    tls: bool = Field(True, description="Whether to enable TLS/HTTPS")
    rules: List[IngressRule] = Field(default_factory=list, description="Routing rules")


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
