import dotenv
dotenv.load_dotenv()

import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, projects, github, project_terminal, k8s_diagram
from app.routers import deploy
from app.config import settings

app = FastAPI()

# CORS middleware - allow frontend to make requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth")
app.include_router(deploy.router, prefix="/deploy")
app.include_router(projects.router, prefix="/api/projects")
app.include_router(k8s_diagram.router, prefix="/api/k8s")
app.include_router(github.router, prefix="/api/github")
app.include_router(project_terminal.router, prefix="/ws/terminal")
from app.utils.kafka_project_build_consumer import consumer_instance


@app.on_event("startup")
async def _start_background_consumers():
    # Start Kafka consumer for project build events
    asyncio.create_task(consumer_instance.start())


@app.on_event("shutdown")
async def _stop_background_consumers():
    await consumer_instance.stop()
# @app.get("/")
# async def root():
#     return {"message": "Hello Worlds"}