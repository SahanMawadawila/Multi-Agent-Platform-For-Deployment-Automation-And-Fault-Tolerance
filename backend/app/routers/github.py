"""
UI routes for GitHub-related operations.
"""
from fastapi import APIRouter, Depends, Response, Request, BackgroundTasks, Header
from sqlalchemy.ext.asyncio import AsyncSession
from .deps import get_db
from ..models import User
from app.models import OauthToken, UserProject
from sqlalchemy.future import select
from app.deps import get_current_user
from app.utils.webhook_utils import verify_webhook_signature, parse_repo_from_url
from app.utils.git_mirror_sync import GitMirrorSync
from app.config import settings
import os
import requests
import time
import asyncio
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
                    # Remove .git suffix if present
                    if repo.endswith(".git"):
                        repo = repo[:-4]
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

    # Fallback: unauthenticated request using the API URL
    resp = requests.get(api_url, headers=headers)
    print(f"Fallback unauthenticated check status: {resp.status_code}")
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

    # Required scopes:
    # - repo: Full control of private repositories (read/write)
    # - admin:repo_hook: Full control of repository hooks (for webhooks)
    params = {
        "client_id": github_client_id,
        "redirect_uri": "http://127.0.0.1:8000/api/github/oauth-callback/",
        "state": token,
        "scope": "repo admin:repo_hook",
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


"""
POST /api/github/webhook-push/
Receives push events from GitHub webhooks and syncs code to mirror repository.
"""
@router.post("/webhook-push/")
async def github_webhook_push(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
    x_github_event: str = Header(None, alias="X-GitHub-Event")
):
    """
    Handle GitHub webhook push events.
    When a push is made to the original repo, sync changes to the mirror.
    """
    # Get raw body for signature verification
    body = await request.body()
    
    # Parse JSON payload
    try:
        payload = await request.json()
    except Exception:
        return {"error": "Invalid JSON payload"}, 400
    
    # Extract repository info from payload
    repo_data = payload.get("repository", {})
    repo_full_name = repo_data.get("full_name", "")  # e.g., "owner/repo"
    repo_clone_url = repo_data.get("clone_url", "")  # e.g., "https://github.com/owner/repo.git"
    
    if not repo_full_name:
        print("⚠️ Webhook received but no repository info found")
        return {"error": "No repository info in payload"}
    
    print(f"📥 Webhook received for: {repo_full_name} (event: {x_github_event})")
    
    # Only process push events
    if x_github_event != "push":
        print(f"ℹ️ Ignoring non-push event: {x_github_event}")
        return {"message": f"Ignoring event type: {x_github_event}"}
    
    # Find project(s) that use this repository
    # Match by github_url (could be with or without .git suffix)
    result = await db.execute(
        select(UserProject).where(
            UserProject.github_url.ilike(f"%{repo_full_name}%")
        )
    )
    projects = result.scalars().all()
    
    if not projects:
        print(f"⚠️ No projects found for repo: {repo_full_name}")
        return {"message": "No matching projects found"}
    
    # Verify signature for each matching project
    verified_projects = []
    for project in projects:
        if project.webhook_secret:
            if verify_webhook_signature(body, x_hub_signature_256 or "", project.webhook_secret):
                verified_projects.append(project)
                print(f"✅ Signature verified for project: {project.project_id}")
            else:
                print(f"❌ Signature verification failed for project: {project.project_id}")
        else:
            # No secret configured, skip verification (not recommended for production)
            verified_projects.append(project)
            print(f"⚠️ No webhook secret for project: {project.project_id}, skipping verification")
    
    if not verified_projects:
        return {"error": "Signature verification failed for all matching projects"}, 401
    
    # Get commit info from payload
    head_commit = payload.get("head_commit", {})
    commit_id = head_commit.get("id", "unknown")
    commit_message = head_commit.get("message", "")
    pusher = payload.get("pusher", {}).get("name", "unknown")
    
    print(f"📦 Push by {pusher}: {commit_message[:50]}... (commit: {commit_id[:8]})")
    
    # Trigger sync for each verified project
    for project in verified_projects:
        background_tasks.add_task(
            sync_mirror_from_webhook,
            str(project.project_id),
            project.github_url,
            project.mirror_name,
            project.env_vars or {},
            commit_id
        )
    
    return {
        "message": f"Sync triggered for {len(verified_projects)} project(s)",
        "commit": commit_id[:8],
        "projects": [str(p.project_id) for p in verified_projects]
    }


async def sync_mirror_from_webhook(
    project_id: str,
    github_url: str,
    mirror_name: str,
    env_vars: dict,
    commit_id: str
):
    """
    Background task to sync code from original repo to mirror.
    Called when a webhook push event is received.
    """
    from app.utils.terminal.terminal_send_message import send_terminal_message
    from app.utils.project_deploy_trigger import trigger_deployment_process
    
    print(f"🔄 Starting webhook sync for project {project_id}")
    send_terminal_message(project_id, f"📥 Received push webhook (commit: {commit_id[:8]})\n\r")
    
    try:
        # Initialize mirror sync manager
        manager = GitMirrorSync(settings.GITHUB_TOKEN, settings.GITHUB_ORG)
        
        send_terminal_message(project_id, "🔄 Syncing changes to mirror repository...\n\r")
        
        # Sync the code (this pulls from original and pushes to mirror)
        sync_result = await asyncio.to_thread(
            manager.sync_code,
            github_url,
            mirror_name,
            env_vars
        )
        
        mirror_url, synced_commit = (sync_result if isinstance(sync_result, tuple) else (sync_result, None))
        
        send_terminal_message(project_id, f"✅ Mirror updated successfully!\n\r")
        send_terminal_message(project_id, f"🚀 Triggering new deployment...\n\r")
        
        # Trigger full deployment (Kafka job)
        await trigger_deployment_process(project_id)
        
    except Exception as e:
        print(f"❌ Webhook sync failed for {project_id}: {e}")
        send_terminal_message(project_id, f"❌ Sync failed: {str(e)}\n\r")