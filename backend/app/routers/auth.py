from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .deps import get_db
# from ..models import User
from app.models import User
from sqlalchemy.future import select
from app.security import create_access_token

router = APIRouter()

@router.post("/sync")
async def sync_user(user: dict, db: AsyncSession = Depends(get_db)):
    email = user["email"]
    provider = user["provider"]
    provider_id = user["provider_id"]
    name = user.get("name")
    image = user.get("image")

    result = await db.execute(select(User).where(User.provider_id == provider_id))
    existing = result.scalars().first()

    if existing:
        user_id = existing.id
    else:
        new_user = User(
            email=email,
            provider=provider,
            provider_id=provider_id,
            name=name,
            image=image
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        user_id = new_user.id

    # create JWT token
    access_token = create_access_token({"sub": str(user_id)})
    return {"access_token": access_token, "token_type": "bearer"}