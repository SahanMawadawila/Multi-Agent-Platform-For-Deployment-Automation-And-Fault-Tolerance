import dotenv
dotenv.load_dotenv()

from fastapi import FastAPI
from app.routers import auth

app = FastAPI()

app.include_router(auth.router, prefix="/auth")

# @app.get("/")
# async def root():
#     return {"message": "Hello Worlds"}