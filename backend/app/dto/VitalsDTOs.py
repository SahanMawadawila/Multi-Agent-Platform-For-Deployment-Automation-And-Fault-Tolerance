from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class DeploymentVitalOutDTO(BaseModel):
    vital_id: int
    project_id: UUID
    namespace: str
    pod_name: str
    pod_phase: Optional[str] = None
    cpu_millicores: int
    memory_mebibytes: int
    probe_status: Optional[str] = None
    probe_latency_ms: Optional[int] = None
    sampled_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True
