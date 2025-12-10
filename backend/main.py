import dotenv
dotenv.load_dotenv()

from fastapi import FastAPI
from app.routers import auth, projects

app = FastAPI()

app.include_router(auth.router, prefix="/auth")
app.include_router(projects.router, prefix="/api/projects")

# @app.get("/")
# async def root():
#     return {"message": "Hello Worlds"}