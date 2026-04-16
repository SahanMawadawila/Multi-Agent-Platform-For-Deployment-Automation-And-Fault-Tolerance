import asyncio
import json
from aiokafka import AIOKafkaConsumer
from sqlalchemy import select
from app.database.database import SessionLocal
from app.models.project_builds import ProjectBuild, BuildStatus
from app.models.user_project import UserProject
from app.config import settings


class ProjectBuildEventConsumer:
    def __init__(self, topic: str = "project-build-events"):
        self.topic = topic
        self._task = None
        self._stop_event = asyncio.Event()

    async def start(self):
        loop = asyncio.get_running_loop()
        self.consumer = AIOKafkaConsumer(
            self.topic,
            loop=loop,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=getattr(settings, "KAFKA_GROUP_ID", "project-build-events-group"),
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="earliest",
        )
        await self.consumer.start()
        self._task = asyncio.create_task(self._consume_loop())

    async def stop(self):
        self._stop_event.set()
        if self._task:
            await self._task
        if hasattr(self, "consumer"):
            await self.consumer.stop()

    async def _consume_loop(self):
        try:
            async for msg in self.consumer:
                print(f"\n[Kafka Event] Received msg on {msg.topic}: {msg.value.get('event_type') if isinstance(msg.value, dict) else 'unknown'}")
                # msg.value is already deserialized JSON
                await self.handle_event(msg.value)
                if self._stop_event.is_set():
                    break
        except asyncio.CancelledError:
            return

    async def handle_event(self, payload: dict):
        event_type = payload.get("event_type", "build_status")
        
        if event_type == "build_status":
            await self.handle_build_status(payload)
        elif event_type == "plan_result":
            await self.handle_plan_result(payload)

    async def handle_plan_result(self, payload: dict):
        import uuid
        project_id = payload.get("project_id")
        plan_data = payload.get("plan")
        
        if not project_id or not plan_data:
            print(f"Invalid plan result event: {payload}")
            return
            
        print(f"Received deployment plan for project: {project_id}")
        
        try:
            project_uuid = uuid.UUID(project_id)
            async with SessionLocal() as session:
                result = await session.execute(
                    select(UserProject).where(UserProject.project_id == project_uuid)
                )
                project = result.scalars().first()
                
                if project:
                    project.deployment_plan = plan_data
                    project.plan_status = "ready"
                    session.add(project)
                    await session.commit()
                    print(f"Successfully saved deployment plan for project: {project_id}")
                else:
                    print(f"Project {project_id} not found when saving plan")
        except Exception as e:
            import traceback
            print(f"Error saving plan to database: {e}")
            traceback.print_exc()

    async def handle_build_status(self, payload: dict):
        # Expected payload keys: project_id, build_id, status, details
        project_id = payload.get("project_id")
        build_id = payload.get("build_id")
        status = payload.get("status")
        details = payload.get("details") or {}

        if build_id is None:
            return

        # Determine new status
        new_status = BuildStatus.failed  # Default to failed if status is unrecognized
        status_str = str(status).lower() if status else ""
        if (status_str == "in_progress" or status_str == "in-process"):
            new_status = BuildStatus.in_process
        elif (status_str == "success"):
            new_status = BuildStatus.success
        # elif (status_str == "failed"):
        #     new_status = BuildStatus.failed

        async with SessionLocal() as session:
            stmt = select(ProjectBuild).where(ProjectBuild.build_id == int(build_id))
            if project_id:
                stmt = stmt.where(ProjectBuild.project_id == project_id)

            result = await session.execute(stmt)
            build = result.scalars().first()
            if not build:
                return

            build.build_status = new_status
            

            # Handle details if it's a dict (success event with access_url, is_current)
            if isinstance(details, dict):
                
                # Handle success: set is_current and clear from other builds
                if details.get("is_current") and new_status == BuildStatus.success:
                    # Clear is_current from all other builds for this project
                    await session.execute(
                        ProjectBuild.__table__.update()
                        .where(ProjectBuild.project_id == build.project_id)
                        .where(ProjectBuild.build_id != build.build_id)
                        .values(is_current=False)
                    )
                    build.is_current = True
                
                # Update access_url in user_projects table
                if details.get("access_url"):
                    await session.execute(
                        UserProject.__table__.update()
                        .where(UserProject.project_id == build.project_id)
                        .values(project_access_url=details["access_url"])
                    )
                
                # Store gitops_commit_id for rollback
                if details.get("gitops_commit_id"):
                    build.gitops_commit_id = details["gitops_commit_id"]

                # Store duration
                if details.get("duration") is not None:
                    build.duration = details["duration"]

            await session.commit()


consumer_instance = ProjectBuildEventConsumer()
