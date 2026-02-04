from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from .deps import get_db
# from ..models import User
from app.models import User, RefreshToken
from sqlalchemy.future import select
from datetime import datetime
from app.security import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    get_token_expiry_timestamp
)

router = APIRouter()


class RefreshTokenRequest(BaseModel):
    refresh_token: str


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

    # Create both access and refresh tokens
    access_token = create_access_token({"sub": str(user_id)})
    refresh_token, jti, expires_at = create_refresh_token({"sub": str(user_id)})
    
    # Store refresh token in database for revocation support
    db_refresh_token = RefreshToken(
        jti=jti,
        user_id=user_id,
        expires_at=expires_at
    )
    db.add(db_refresh_token)
    await db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user_id": user_id,
        "expires_at": get_token_expiry_timestamp()
    }


@router.post("/refresh")
async def refresh_access_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Refresh an expired access token using a valid refresh token."""
    payload = verify_refresh_token(request.refresh_token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    
    user_id = payload.get("sub")
    jti = payload.get("jti")
    
    if not user_id or not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    # Check if refresh token exists and is not revoked
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.jti == jti,
            RefreshToken.revoked == False
        )
    )
    db_token = result.scalars().first()
    
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )
    
    # Verify user still exists
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    # Create new access token
    new_access_token = create_access_token({"sub": str(user_id)})
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_at": get_token_expiry_timestamp()
    }


@router.post("/revoke")
async def revoke_refresh_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Revoke a refresh token (e.g., on logout)."""
    payload = verify_refresh_token(request.refresh_token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid refresh token",
        )
    
    jti = payload.get("jti")
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token payload",
        )
    
    result = await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
    db_token = result.scalars().first()
    
    if db_token:
        db_token.revoked = True
        await db.commit()
    
    return {"message": "Token revoked successfully"}