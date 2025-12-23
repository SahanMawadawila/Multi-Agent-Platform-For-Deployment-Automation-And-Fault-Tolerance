import dotenv
dotenv.load_dotenv()

from fastapi import FastAPI
from app.routers import auth
from app.routers import deploy

app = FastAPI()

app.include_router(auth.router, prefix="/auth")
app.include_router(deploy.router, prefix="/deploy")

# @app.get("/")
# async def root():
#     return {"message": "Hello Worlds"}