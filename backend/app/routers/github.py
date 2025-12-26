"""
UI routes for GitHub-related operations.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .deps import get_db
# from ..models import User
from app.models import UserProject
from sqlalchemy.future import select
from app.deps import get_current_user

import requests

router = APIRouter()


"""
GET /github/check-repo-accessible/
"""
@router.get("/check-repo-accessible/")
async def check_repo_accessible(
    repo_url: str,
    db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    print("Authenticated user:", user)

    # Here you would add the logic to check if the repository is accessible.
    # This is a placeholder implementation.

    is_accessible = False
    is_private = False

    response = requests.get(repo_url)
    print("GitHub response status:", response.status_code)
    if response.status_code == 200:
        is_accessible = True
    elif response.status_code == 404:
        # Could be private. Check user has access token
        user_access_token = ""  # Fetch from DB based on user
        if not user_access_token:
            is_accessible = False
        else:
            headers = {
                "Authorization": f"token {user_access_token}",
                "Accept": "application/vnd.github.v3+json",
            }
            auth_response = requests.get(repo_url, headers=headers)
            is_accessible = auth_response.status_code == 200
            is_private = True
    else:
        is_accessible = False  # Replace with actual check

    return {
        "is_accessible": is_accessible,
        "is_private": is_private
    }
    

"""
GET /github/get-access-request-url/
"""
@router.get("/get-access-request-url/")
async def get_access_request_url(
    repo_url: str,
    db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    print("Authenticated user:", user)

    # Here you would add the logic to generate the access request URL.
    # This is a placeholder implementation.
    return {
        "access_request_url": ""
    }



"""
GET /github/oauth-callback/
"""
@router.get("/oauth-callback/")
async def github_oauth_callback(
    code: str,
    db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    print("Authenticated user:", user)

    # Here you would add the logic to handle the OAuth callback.
    # This is a placeholder implementation.
    return {
        "message": "OAuth callback received",
        "code": code
    }