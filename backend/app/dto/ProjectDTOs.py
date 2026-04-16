from pydantic import BaseModel
from typing import Optional, Dict
from uuid import UUID
from datetime import datetime

class UserProjectSimpleOutDTO(BaseModel):
    project_id: UUID
    project_name: str
    domain_name: Optional[str]
    status: Optional[str]

    class Config:
        orm_mode = True
        from_attributes = True



class UserProjectDetailOutDTO(BaseModel):
    project_id: UUID
    project_name: str
    github_url: Optional[str] = None
    is_auto_deploy_enabled: bool
    domain_name: Optional[str] = None
    status: Optional[str] = None
    topology_info: Optional[dict] = None
    env_vars: Optional[Dict] = None
    deployment_plan: Optional[dict] = None
    plan_status: Optional[str] = None
    project_access_url: Optional[str] = None

    class Config:
        orm_mode = True
        from_attributes = True


class ProjectCreateInDTO(BaseModel):
    project_name: str
    repository_url: str
    env_vars: Optional[Dict] = None
    trigger_deployment: Optional[bool] = False



class ProjectDeploymentOutDTO(BaseModel):
    build_id: int
    project_id: UUID
    build_date: datetime
    build_status: str
    commit_id: Optional[str] = None
    build_version: Optional[str] = None
    duration: Optional[int] = None
    is_current: bool = False

    class Config:
        orm_mode = True
        from_attributes = True
