"""
UI routes for GitHub-related operations.
"""
from fastapi import APIRouter, Depends, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from .deps import get_db
from ..models import User
from app.models import OauthToken
from sqlalchemy.future import select
from app.deps import get_current_user
import os
import requests
import time
from urllib.parse import urlparse
from datetime import datetime, timedelta, timezone
from jwt import PyJWT

router = APIRouter()

"""
DO NOT COMM
"""
GITHUB_AUTH_SALT = "some_random_salt_for_github_oauth_xw3333"

deployment_env = os.getenv("DEPLOYMENT_ENV", "development")
github_client_id = os.getenv("GITHUB_CLIENT_ID", "")
github_secret = os.getenv("GITHUB_CLIENT_SECRET", "")

cookie_name = "github_oauth_user_id"

"""
GET /api/github/check-repo-accessible/
"""
@router.get("/check-repo-accessible/")
async def check_repo_accessible(
    repo_url: str,
    db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    print("Authenticated user:", user)

    # Try to use the user's GitHub OAuth token (if present) to check repo access.
    headers = {"Accept": "application/vnd.github.v3+json"}

    # Normalize repo_url into GitHub API repo endpoint if necessary.
    def to_api_repo_url(raw_url: str) -> str:
        # Accept raw API URL, web URL, or shorthand like "owner/repo"
        raw_url = raw_url.strip()
        if raw_url.startswith("https://api.github.com/repos/"):
            return raw_url
        # shorthand owner/repo
        if "/" in raw_url and not raw_url.startswith("http"):
            parts = raw_url.strip("/").split("/")
            if len(parts) >= 2:
                owner, repo = parts[0], parts[1]
                return f"https://api.github.com/repos/{owner}/{repo}"
        # try parsing web URL
        try:
            p = urlparse(raw_url)
            if p.netloc.endswith("github.com"):
                segs = [s for s in p.path.split("/") if s]
                if len(segs) >= 2:
                    owner, repo = segs[0], segs[1]
                    return f"https://api.github.com/repos/{owner}/{repo}"
        except Exception:
            pass
        # fallback to original
        return raw_url

    api_url = to_api_repo_url(repo_url)
    print("Checking repo via API URL:", api_url)

    result = await db.execute(
        select(OauthToken)
        .where(OauthToken.user_id == int(user["id"]))
        .where(OauthToken.provider == "github")
    )
    oauth_token = result.scalars().first()

    # No stored token: perform unauthenticated request
    if not oauth_token:
        resp = requests.get(api_url, headers=headers)
        return {"is_accessible": resp.status_code == 200, "is_private": resp.status_code == 404}

    # Determine if access token is expired (DB stores naive UTC datetimes)
    now = datetime.utcnow()
    access_token = oauth_token.access_token
    if oauth_token.access_token_expires_at and oauth_token.access_token_expires_at <= now:
        # Try to refresh using refresh token
        if oauth_token.refresh_token:
            token_url = "https://github.com/login/oauth/access_token"
            data = {
                "client_id": github_client_id,
                "client_secret": github_secret,
                "grant_type": "refresh_token",
                "refresh_token": oauth_token.refresh_token,
            }
            token_resp = requests.post(token_url, data=data, headers={"Accept": "application/json"})
            if token_resp.status_code == 200:
                j = token_resp.json()
                access_token = j.get("access_token")
                expires_in = j.get("expires_in")
                refresh_token = j.get("refresh_token")
                refresh_expires_in = j.get("refresh_token_expires_in")

                oauth_token.access_token = access_token
                oauth_token.refresh_token = refresh_token or oauth_token.refresh_token
                oauth_token.access_token_expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).replace(tzinfo=None) if expires_in else None
                oauth_token.refresh_token_expires_at = (datetime.utcnow() + timedelta(seconds=refresh_expires_in)).replace(tzinfo=None) if refresh_expires_in else None
                oauth_token.updated_at = datetime.utcnow().replace(tzinfo=None)
                db.add(oauth_token)
                await db.commit()

    # Use the (possibly refreshed) access token if available
    if access_token:
        auth_headers = {**headers, "Authorization": f"token {access_token}"}
        resp = requests.get(api_url, headers=auth_headers)
        print("The response status code with auth:", resp.status_code)
        if resp.status_code == 200:
            return {"is_accessible": True, "is_private": False}
        if resp.status_code == 404:
            return {"is_accessible": False, "is_private": True}
        # For other statuses (401, etc.) fall through to unauthenticated check

    # Fallback: unauthenticated request
    resp = requests.get(repo_url, headers=headers)
    return {"is_accessible": resp.status_code == 200, "is_private": resp.status_code == 404}
    

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
    if user_id is None:
        return {
            "message": "Invalid state token data",
            "code": code
        }
    # Ensure user_id is an integer to match DB column type
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return {
            "message": "Invalid state token data: user_id must be an integer",
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
    result = await db.execute(
        select(OauthToken)
        .where(OauthToken.user_id == user_id)
        .where(OauthToken.provider == "github")
    )
    existing_tokens = result.scalars().all()
    for token in existing_tokens:
        await db.delete(token)
    await db.commit()

    # Store new token
    oauth_token = OauthToken(
        user_id=user_id,
        provider="github",
        access_token=access_token,
        refresh_token=refresh_token,
        access_token_expires_at=((datetime.now(timezone.utc) + timedelta(seconds=expires_in)).replace(tzinfo=None)) if expires_in else None,
        refresh_token_expires_at=((datetime.now(timezone.utc) + timedelta(seconds=refresh_token_expires_in)).replace(tzinfo=None)) if refresh_token_expires_in else None,
        scope=scope,
        token_type=token_type,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(oauth_token)
    await db.commit()

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