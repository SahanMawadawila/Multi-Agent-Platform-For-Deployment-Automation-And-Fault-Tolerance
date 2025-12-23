from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.routers.deps import get_db
from app.models.user_project import UserProject
from app.config import settings
from kafka import KafkaProducer
import json
from app.utils.git_mirror_sync import GitMirrorSync

router = APIRouter()

# Use settings from centralized config
producer = KafkaProducer(
    bootstrap_servers=[settings.KAFKA_BOOTSTRAP_SERVERS],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)


manager = GitMirrorSync(settings.GITHUB_TOKEN, settings.GITHUB_ORG)

def on_user_click_deploy(user_repo_url, project_id):
    """
    This runs immediately when user clicks 'Deploy'.
    """
    mirror_name = f"mirror-{project_id}"
    
    # 1. Create the empty bucket
    manager.create_private_mirror(mirror_name)
    
    # 2. Fill it with user's code
    manager.sync_code(user_repo_url, mirror_name)
    
    # 3. NOW fire the Kafka Event for the Agent
    kafka_payload = {
        "action": "start_agent",
        "repo_url": f"https://github.com/{settings.GITHUB_ORG}/{mirror_name}.git" 
        # Agent now works on YOUR private repo, not the user's
    }

@router.post("/")
async def trigger_deploy(payload: dict, db: AsyncSession = Depends(get_db)):

    #1. upload to database
    new_project = UserProject(
        owner_id=payload["owner_id"],
        project_name=payload["project_name"],
        github_url=payload["github_url"],
        is_auto_deploy_enabled=True,
        domain_name="myapp.example.com",
        status="active",
        topology_info={"nodes": ["frontend", "backend"]},
        env_variables={"PORT": "3000", "NODE_ENV": "production"}
    )

    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)
    project_id = new_project.project_id

    #2. Create github mirror and sync code
    mirror_name = f"mirror-{project_id}"
    manager.create_private_mirror(mirror_name)
    manager.sync_code(payload["github_url"], mirror_name)
    #3. Trigger kafka job for agent
    kafka_payload = {
        "action": 'agent-jobs',
        "repo_url": f"https://github.com/{settings.GITHUB_ORG}/{mirror_name}.git"
    }

    #2. send message to kafka
    producer.send(settings.KAFKA_TOPIC_AGENT_JOBS, value=kafka_payload)
    producer.flush()
    return {"status": "Job sent to Kafka"}