"""
Docstring for app.routers.project_terminal
Creates a websocket for frontend terminal to connect to backend terminal session.
"""

import asyncio
from fastapi import APIRouter, Depends, Response
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from .deps import get_db
from app.models import UserProject, User
from sqlalchemy.future import select
from app.deps import get_current_user
from jwt import PyJWT
import time as t
import random
from app.utils.terminal.terminal_fan_out import register, unregister, kafka_listener

router = APIRouter()
WS_AUTH_COOKIE_NAME = "ws_terminal_auth_token"
WS_AUTH_SALT = "some_random_salt"

"""
Generate a random token for websocket authentication
"""
def get_random_token(project_id: str, user_id) -> str:
    random_token = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=32))
    exp = t.time() + 300  # 5 minutes expiry
    raw_token = f"{random_token}|{project_id}|{user_id}|{exp}"
    jwt_instance = PyJWT()
    token = jwt_instance.encode({"data": raw_token}, WS_AUTH_SALT, algorithm="HS256")
    return token


async def verify_hashed_token(token: str, project_id: str) -> int|None:
    jwt_instance = PyJWT()
    try:
        decoded = jwt_instance.decode(token, WS_AUTH_SALT, algorithms=["HS256"])
    except:
        return None
    raw_token = decoded.get("data")


    splits = raw_token.split("|")
    if len(splits) != 4:
        return None
    _, t_project_id, t_user_id, exp = splits
    
    if t.time() > float(exp):
        return None
    
    if t_project_id != project_id:
        return None
    return int(t_user_id)



@router.post("/authorize/{project_id}")
async def project_terminal_authorize_websocket(
    project_id: str,
    response: Response,
    db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    # User must own the project
    result = await db.execute(
        select(UserProject)
        .where(UserProject.project_id == project_id)
        .where(UserProject.owner_id == int(user["id"]))
    )
    # Generate token
    project = result.scalars().first()
    
    if not project:
        # 401 Unauthorized
        return {"authorized": False}
    
    token = get_random_token(project_id, user["id"])
    response.set_cookie(
        key=WS_AUTH_COOKIE_NAME,
        value=token,
        httponly=False,
        max_age=3600,  # 5 minutes
        secure=False,  # Set to True only in production with HTTPS
        samesite="None" if False else None  # None with secure=True for cross-site, None for dev
    )

    return {"authorized": True, "ws_auth_token": token}

    

"""
Terminal opens a websocket connection to this endpoint.
Application uses Kafka to listen to messages from backend terminal session and
sends them to the frontend terminal. Only works one-way for now (backend to frontend).
"""
@router.websocket("/{project_id}")
async def project_terminal_websocket(
    websocket: WebSocket,
    project_id: str,
    db: AsyncSession = Depends(get_db)):

    try:
        ## Authentication can be added here
        token = websocket.query_params.get("token")
        if not token:
            print("Missing token", websocket.query_params)
            await websocket.close(code=1008)
            return
        
        user_id = await verify_hashed_token(token, project_id)
        if not user_id:
            print("Token verification failed")
            await websocket.close(code=1008)
            return
        
                
        user = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user.scalars().first()

        if not user:
            await websocket.close(code=1008)
            return
        # User must own the project
        result = await db.execute(
            select(UserProject)
            .where(UserProject.project_id == project_id)
            .where(UserProject.owner_id == int(user.id))
        )
        project = result.scalars().first()
        if not project:
            await websocket.close(code=1008)
            return

        
        await websocket.accept()
        await register(websocket, project_id)

        # Send initial message to client
        current_time = t.strftime("%Y-%m-%d %H:%M:%S", t.gmtime())
        await websocket.send_text(f"{current_time} - Terminal connected to project \033[33m{project.project_name}\033[0m.\n\r")
        
        try:
            while True:
                # Keep connection alive and listen for disconnect
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            await unregister(websocket, project_id)

    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close(code=1011)

@router.on_event("startup")
async def startup_event():
    asyncio.create_task(kafka_listener())