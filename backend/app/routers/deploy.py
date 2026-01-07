from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.routers.deps import get_db
from app.deps import get_current_user
from app.models.user_project import UserProject
from app.config import settings
from kafka import KafkaProducer
import json
from app.utils.git_mirror_sync import GitMirrorSync
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


# Pydantic model for request validation
class CreateProjectRequest(BaseModel):
    project_name: str
    github_url: str
    project_type: Optional[str] = None
    env_variables: Optional[dict] = None


# Lazy-load Kafka producer to avoid connection errors at startup
def get_kafka_producer():
    return KafkaProducer(
        bootstrap_servers=[settings.KAFKA_BOOTSTRAP_SERVERS],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )


manager = GitMirrorSync(settings.GITHUB_TOKEN, settings.GITHUB_ORG)

@router.post("/")
async def trigger_deploy(
    request: CreateProjectRequest,
    current_user: dict = Depends(get_current_user),  # Protected route
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new project and trigger deployment.
    This route is protected - requires valid JWT token.
    """
    user_id = int(current_user["id"])

    # 1. Save to database
    new_project = UserProject(
        owner_id=user_id,
        project_name=request.project_name,
        github_url=request.github_url,
        is_auto_deploy_enabled=True,
        status="pending",
    )

    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)
    project_id = new_project.project_id

    # 2. Create github mirror and sync code (includes .env file if provided)
    mirror_name = f"mirror-{project_id}"
    manager.create_private_mirror(mirror_name)
    manager.sync_code(request.github_url, mirror_name, request.env_variables)

   
    # 4. Trigger kafka job for agent
    kafka_payload = {
        "action": 'agent-jobs',
        "project_id": str(project_id),
        "repo_url": f"https://github.com/{settings.GITHUB_ORG}/{mirror_name}.git"
    }

    # 5. Send message to kafka
    producer = get_kafka_producer()
    producer.send(settings.KAFKA_TOPIC_AGENT_JOBS, value=kafka_payload)
    producer.flush()
    
    return {
        "status": "Job sent to Kafka",
        "project_id": str(project_id),
        "project_name": request.project_name
    }