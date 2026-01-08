"""
UI routes for GitHub-related operations.
"""
from fastapi import APIRouter, Depends, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from .deps import get_db
# from ..models import User
# from app.models import OauthToken
from sqlalchemy.future import select
from app.deps import get_current_user
import os
import requests
import time
from jwt import PyJWT

router = APIRouter()

"""
DO NOT COMM
"""
GITHUB_AUTH_SALT = "some_random_salt_for_github_oauth_xw3333"

deployment_env = os.getenv("DEPLOYMENT_ENV", "development")
github_client_id = os.getenv("GITHUB_CLIENT_ID_NAMI", "")
github_secret = os.getenv("GITHUB_SECRET_NAMI", "")

cookie_name = "github_oauth_user_id"

"""
GET /api/github/check-repo-accessible/
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
GET /api/github/get-access-request-url/
"""
@router.get("/get-access-request-url/")
async def get_access_request_url(
    db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):

    # Create signed JWT for state parameter
    jwt_instance = PyJWT()
    token = jwt_instance.encode({"user_id": user["id"], 'exp': time.time() + 600}, GITHUB_AUTH_SALT, algorithm="HS256")

    params = {
        "client_id": github_client_id,
        "redirect_uri": "http://127.0.0.1:8000/api/github/oauth-callback/",
        "state": token,
    }

    url = "https://github.com/login/oauth/authorize" + "?" + "&".join([f"{k}={v}" for k, v in params.items()])

    return {
        "access_request_url": url
    }



"""
GET /api/github/oauth-callback/
"""
@router.get("/oauth-callback/")
async def github_oauth_callback(
    state: str,
    code: str, db: AsyncSession = Depends(get_db)):

    if (not code) or (code.strip() == ""):
        return {
            "message": "Invalid code",
            "code": code
        }
    

    # Verify state token
    jwt_instance = PyJWT()
    try:
        decoded = jwt_instance.decode(state, GITHUB_AUTH_SALT, algorithms=["HS256"])
    except:
        return {
            "message": "Invalid state token",
            "code": code
        }
    user_id = decoded.get("user_id")
    if not user_id:
        return {
            "message": "Invalid state token data",
            "code": code
        }
    
    # Exchange code for access token
    url = "https://github.com/login/oauth/access_token"
    data = {
        "client_id": github_client_id,
        "client_secret": github_secret,
        "code": code
    }
    headers = {
        "Accept": "application/json"
    }
    response = requests.post(url, data=data, headers=headers)

    if response.status_code != 200:
        return {
            "message": "Failed to get access token",
            "code": code
        }
    access_token = response.json().get("access_token")
    expires_in = response.json().get("expires_in")
    refresh_token = response.json().get("refresh_token")
    refresh_token_expires_in = response.json().get("refresh_token_expires_in")
    scope = response.json().get("scope")
    token_type = response.json().get("token_type")
    # https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/refreshing-user-access-tokens

    # Delete existing tokens for this user and provider
    # result = await db.execute(
    #     select(OauthToken)
    #     .where(OauthToken.user_id == user_id)
    #     .where(OauthToken.provider == "github")
    # )
    # existing_tokens = result.scalars().all()
    # for token in existing_tokens:
    #     await db.delete(token)
    # await db.commit()

    # Store new token
    # oauth_token = OauthToken(
    #     user_id=user_id,
    #     provider="github",
    #     access_token=access_token,
    #     refresh_token=refresh_token,
    #     access_token_expires_at=time.time() + expires_in if expires_in else None,
    #     refresh_token_expires_at=time.time() + refresh_token_expires_in if refresh_token_expires_in else None,
    #     scope=scope,
    #     token_type=token_type,
    #     created_at=time.time(),
    #     updated_at=time.time()
    # )
    # db.add(oauth_token)
    # await db.commit()

    # Store these tokens in the database associated with the user

    return {
        "message": "OAuth callback received",
        "for_user_id": user_id,
        "access_token": access_token,
        "expires_in": expires_in,
        "refresh_token": refresh_token,
        "refresh_token_expires_in": refresh_token_expires_in,
        "scope": scope,
        "token_type": token_type,
        "code": code
    }



@router.get("/test-generate-jwt/")
async def test_generate_jwt():
    jwt_instance = PyJWT()
    payload = {
        "iat": time.time(),
        "iss": github_client_id,
        "exp": time.time() + 3600
    }
    private_key_demo = "GicEVapyf4R/wN1P6XNR3HytPFVMzhyFVi3OPfUSrXU="

    token = jwt_instance.encode(payload, private_key_demo, algorithm="HS256")
    return {
        "token": token,
        "payload": payload
    }

"""
POST /api/github/webhook-callback/
"""
@router.post("/webhook-callback/")
async def github_webhook_callback():
    # Here you would add the logic to handle the webhook callback.
    # This is a placeholder implementation.
    return {
        "message": "Webhook callback received"
    }