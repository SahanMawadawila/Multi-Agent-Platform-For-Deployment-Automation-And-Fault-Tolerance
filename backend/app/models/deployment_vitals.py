from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from . import Base


class DeploymentVital(Base):
    __tablename__ = "deployment_vitals"

    vital_id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_projects.project_id"),
        nullable=False,
        index=True,
    )
    namespace = Column(String, nullable=False, index=True)
    pod_name = Column(String, nullable=False, index=True)
    pod_phase = Column(String, nullable=True)
    cpu_millicores = Column(Integer, nullable=False)
    memory_mebibytes = Column(Integer, nullable=False)
    probe_status = Column(String, nullable=True)
    probe_latency_ms = Column(Integer, nullable=True)
    sampled_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
