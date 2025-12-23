import dotenv
dotenv.load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth
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

# @app.get("/")
# async def root():
#     return {"message": "Hello Worlds"}