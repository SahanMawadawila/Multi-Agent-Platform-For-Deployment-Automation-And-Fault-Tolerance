import asyncio
import json
from aiokafka import AIOKafkaConsumer
from sqlalchemy import select, update
from app.database.database import SessionLocal
from app.models.project_builds import ProjectBuild, BuildStatus
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
                # msg.value is already deserialized JSON
                await self.handle_event(msg.value)
                if self._stop_event.is_set():
                    break
        except asyncio.CancelledError:
            return

    async def handle_event(self, payload: dict):
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
            # Optional: update commit_id if present in details
            commit = details.get("commit_id") if isinstance(details, dict) else None
            if commit:
                build.commit_id = commit

            await session.commit()


consumer_instance = ProjectBuildEventConsumer()
