import dotenv
dotenv.load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, projects, github, project_terminal

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(auth.router, prefix="/auth")
app.include_router(projects.router, prefix="/api/projects")
app.include_router(github.router, prefix="/api/github")
app.include_router(project_terminal.router, prefix="/ws/terminal")
# @app.get("/")
# async def root():
#     return {"message": "Hello Worlds"}