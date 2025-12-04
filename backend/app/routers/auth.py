from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .deps import get_db
# from ..models import User
from app.models import User
from sqlalchemy.future import select

router = APIRouter()

@router.post("/sync")
async def sync_user(user: dict, db: AsyncSession = Depends(get_db)):
    # print("Received user payload:", user) 
    email = user["email"]
    provider = user["provider"]
    provider_id = user["provider_id"]

    # check if user exists
    result = await db.execute(
        select(User).where(User.provider_id == provider_id)
    )
    existing = result.scalars().first()

    if existing:
        return {"status": "ok", "user_id": existing.id}

    # create new user
    new_user = User(
        email=email,
        provider=provider,
        provider_id=provider_id,
        name=user["name"],
        image=user.get("image")
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return {"status": "created", "user_id": new_user.id}
