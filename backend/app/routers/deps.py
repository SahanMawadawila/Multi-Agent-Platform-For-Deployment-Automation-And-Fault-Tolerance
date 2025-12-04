from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.database import SessionLocal

async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
