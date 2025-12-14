"""
Docstring for app.routers.project_terminal
Creates a websocket for frontend terminal to connect to backend terminal session.
"""

import asyncio
from fastapi import APIRouter, Depends, Response
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from .deps import get_db
# from ..models import User
from app.models import UserProject, User
from sqlalchemy.future import select
from app.deps import get_current_user
# from redis.asyncio import Redis
import time as t
import random
from app.database.redis import get_redis_connection
# DTOs
from app.dto.ProjectDTOs import UserProjectSimpleOutDTO, UserProjectDetailOutDTO

router = APIRouter()
WS_AUTH_COOKIE_NAME = "ws_terminal_auth_token"
WS_AUTH_SALT = "some_random_salt"


def get_random_token(project_id: str, user_id) -> str:
    random_token = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=32))
    return f"{random_token}|{project_id}|{user_id}"


async def verify_hashed_token(token: str, project_id: str) -> int|None:
    #r = Redis(host='localhost', port=6379, db=0)
    r = get_redis_connection()

    stored = await r.get(f"WS_TERMINAL_AUTH_{token}")
    
    if not stored:
        await r.close()
        return None
    
    # Remove one time use
    await r.delete(f"WS_TERMINAL_AUTH_{token}")
    await r.close()

    splits = token.split("|")
    if len(splits) != 3:
        return None
    _, t_project_id, t_user_id = splits
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

    # Add token to redis with expiry
    r = get_redis_connection()
    await r.setex(f"WS_TERMINAL_AUTH_{token}", 300, "valid")  # 5 minutes expiry
    await r.close()

    return {"authorized": True, "ws_auth_token": token}

    

"""
@TODO: Add auth guard
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

        
        channel_name = f"PT_{project_id}"
        #r = Redis(host='localhost', port=6379, db=0)
        r = get_redis_connection()
        
        await websocket.accept()
        pubsub = r.pubsub()
        await pubsub.subscribe(channel_name)

        # Send initial message to client
        current_time = t.strftime("%Y-%m-%d %H:%M:%S", t.gmtime())
        await websocket.send_text(f"{current_time} - Terminal connected to project \033[33m{project.project_name}\033[0m.\n")
    except WebSocketDisconnect:
        print("WebSocket disconnected during setup")
        return
    except Exception as e:
        print(f"WebSocket setup error: {e}")
        await websocket.close(code=1011)
        return
    
    # Access granted, start listening to Redis and WebSocket
    async def redis_listener():
        """Listen for messages from Redis and send to WebSocket"""
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    data = message['data'].decode('utf-8') if isinstance(message['data'], bytes) else message['data']
                    print(f"Redis -> WebSocket: {data}")
                    await websocket.send_text(data)
        except Exception as e:
            print(f"Redis listener error: {e}")

    async def websocket_listener():
        """Listen for messages from WebSocket and publish to Redis"""
        try:
            while True:
                data = await websocket.receive_text()
                print(f"WebSocket -> Redis: {data}")
                await r.publish(channel_name, data)
        except WebSocketDisconnect:
            print("WebSocket disconnected")
        except Exception as e:
            print(f"WebSocket listener error: {e}")

    try:
        # Run both listeners concurrently
        await asyncio.gather(
            redis_listener(),
            websocket_listener()
        )
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await pubsub.unsubscribe()
        await pubsub.aclose()
        await r.aclose()
