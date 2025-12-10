from pydantic import BaseModel
from typing import Optional
from uuid import UUID

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
    github_url: Optional[str]
    is_auto_deploy_enabled: bool
    domain_name: Optional[str]
    status: Optional[str]
    topology_info: Optional[dict]
    env_variables: Optional[list]

    class Config:
        orm_mode = True
        from_attributes = True