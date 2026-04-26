from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user
from app.dto.VitalsDTOs import DeploymentVitalOutDTO
from app.models import DeploymentVital, UserProject
from app.routers.deps import get_db

router = APIRouter()


@router.get("/projects/{project_id}/vitals")
async def get_project_vitals(
    project_id: str,
    hours: int = Query(default=24, ge=1, le=720),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    owner_result = await db.execute(
        select(UserProject).where(UserProject.project_id == project_id).where(UserProject.owner_id == int(user["id"]))
    )
    project = owner_result.scalars().first()
    if not project:
        return {"error": "Project not found"}

    cutoff = datetime.utcnow() - timedelta(hours=hours)

    result = await db.execute(
        select(DeploymentVital)
        .where(DeploymentVital.project_id == project_id)
        .where(DeploymentVital.sampled_at >= cutoff)
        .order_by(DeploymentVital.sampled_at.asc())
    )
    samples = [DeploymentVitalOutDTO.from_orm(row) for row in result.scalars().all()]

    latest_result = await db.execute(
        select(DeploymentVital)
        .where(DeploymentVital.project_id == project_id)
        .where(DeploymentVital.sampled_at >= cutoff)
        .order_by(DeploymentVital.sampled_at.desc())
    )
    latest_by_pod = {}
    for row in latest_result.scalars().all():
        if row.pod_name not in latest_by_pod:
            latest_by_pod[row.pod_name] = DeploymentVitalOutDTO.from_orm(row)

    pod_count = len(latest_by_pod)
    total_cpu = sum(item.cpu_millicores for item in latest_by_pod.values())
    total_memory = sum(item.memory_mebibytes for item in latest_by_pod.values())

    return {
        "project_id": project_id,
        "window_hours": hours,
        "sample_count": len(samples),
        "pod_count": pod_count,
        "totals": {
            "cpu_millicores": total_cpu,
            "memory_mebibytes": total_memory,
        },
        "latest": list(latest_by_pod.values()),
        "samples": samples,
    }