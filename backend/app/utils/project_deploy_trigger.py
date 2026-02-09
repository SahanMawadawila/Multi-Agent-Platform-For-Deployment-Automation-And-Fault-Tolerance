from app.config import settings
from kafka import KafkaProducer
import json
from app.models import UserProject, ProjectBuild, BuildStatus
from app.utils.terminal.terminal_send_message import send_terminal_message
from app.utils.git_mirror_sync import GitMirrorSync
from app.utils.webhook_utils import (
    create_webhook, 
    parse_repo_from_url, 
    generate_webhook_secret
)
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
from app.database.database import SessionLocal

manager = GitMirrorSync(settings.GITHUB_TOKEN, settings.GITHUB_ORG)

# Lazy-load Kafka producer to avoid connection errors at startup
def get_kafka_producer():
    return KafkaProducer(
        bootstrap_servers=[settings.KAFKA_BOOTSTRAP_SERVERS],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )


async def get_github_token(user_id: int, db: AsyncSession):
    from app.models.oauth_tokens import OauthToken
    import requests
    from datetime import datetime, timedelta
    from app.config import settings
    # First fetch scalar columns to avoid triggering lazy loads on the ORM object
    result = await db.execute(
        select(
            OauthToken.id,
            OauthToken.access_token,
            OauthToken.refresh_token,
            OauthToken.access_token_expires_at,
            OauthToken.refresh_token_expires_at,
        )
        .where(OauthToken.user_id == user_id)
        .where(OauthToken.provider == 'github')
    )

    row = result.first()
    if not row:
        print("No OAuth token found for user")
        return None

    token_id, access_token, refresh_token, access_expires_at, refresh_expires_at = row

    now = datetime.utcnow()

    # If access token exists and not expired, return it
    if access_token and (not access_expires_at or access_expires_at > now):
        return access_token

    # Access token expired (or missing) — try to refresh if refresh token is available and not expired
    if refresh_token and (not refresh_expires_at or refresh_expires_at > now):
        token_url = "https://github.com/login/oauth/access_token"
        data = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        try:
            resp = requests.post(token_url, data=data, headers={"Accept": "application/json"}, timeout=10)
        except Exception:
            return None

        if resp.status_code != 200:
            return None

        j = resp.json()
        if j.get("error"):
            print(f"Error refreshing GitHub token: {j.get('error_description')}")
            return None

        new_access = j.get("access_token")
        expires_in = j.get("expires_in")
        new_refresh = j.get("refresh_token")
        refresh_expires_in = j.get("refresh_token_expires_in")

        if not new_access:
            return None

        # Load the full ORM object to persist updates
        result2 = await db.execute(
            select(OauthToken).where(OauthToken.id == token_id)
        )
        token_obj = result2.scalars().first()
        if not token_obj:
            return None

        token_obj.access_token = new_access
        token_obj.refresh_token = new_refresh or token_obj.refresh_token
        token_obj.access_token_expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).replace(tzinfo=None) if expires_in else None
        token_obj.refresh_token_expires_at = (datetime.utcnow() + timedelta(seconds=refresh_expires_in)).replace(tzinfo=None) if refresh_expires_in else None
        token_obj.updated_at = datetime.utcnow().replace(tzinfo=None)

        db.add(token_obj)
        await db.commit()
        return token_obj.access_token

    # No valid access token and refresh not available/expired
    return None
    
    

async def trigger_deployment_process(project_id: str):
    # Get the project from the database
    async with SessionLocal() as db:
        print(f"Triggering deployment process for project ID: {project_id}")
        await asyncio.sleep(1)  # small delay before starting
        result = await db.execute(select(UserProject).where(UserProject.project_id == project_id))
        project = result.scalars().first()
        if not project:
            print(f"Project with ID {project_id} not found.")
            return
        
        send_terminal_message(str(project_id), "Starting deployment process...\n\r")

        # Step 1: Check github mirror already exists
        # Mirror name is deterministic based on project_id
        mirror_name = f"mirror-{project_id}"
        access_token = await get_github_token(project.owner_id, db)

        try:
            send_terminal_message(str(project_id), "Cloning and syncing code from GitHub...\\n\\r")
            # Create mirror repo (handles existing repos gracefully - returns existing URL if 422)
            await asyncio.to_thread(manager.create_private_mirror, mirror_name)
            print(f"Using mirror repository: {mirror_name}")
            # Run the blocking sync in a thread so we don't perform IO on the event loop
            sync_result = await asyncio.to_thread(
                manager.sync_code,
                project.github_url,
                mirror_name,
                project.env_vars or {},
                # pass the user's access token so private repos can be cloned
                source_access_token=access_token,
            )

            # sync_result is (mirror_repo_url, commit_id)
            mirror_url, commit_id = (sync_result if isinstance(sync_result, tuple) else (sync_result, None))
            send_terminal_message(project_id, f"Code synchronized from GitHub. commit={commit_id}\n\r")

            # Step 1.5: Setup webhook for auto-sync (only if not already configured)
            # Use user's OAuth token if available, otherwise fall back to platform token
            webhook_token = access_token or settings.GITHUB_TOKEN
            
            if project.webhook_id is None and settings.WEBHOOK_BASE_URL:
                if not webhook_token:
                    print(f"⚠️ No GitHub token available for webhook creation (user OAuth or GITHUB_TOKEN)")
                    send_terminal_message(project_id, "⚠️ Skipping webhook setup (no GitHub token available)\n\r")
                else:
                    send_terminal_message(project_id, "🔗 Setting up auto-sync webhook...\n\r")
                    
                    # Parse owner/repo from github_url
                    owner, repo = parse_repo_from_url(project.github_url)
                    print(f"📌 Parsed repo: owner={owner}, repo={repo} from {project.github_url}")
                    
                    if owner and repo:
                        # Generate a unique secret for this project
                        webhook_secret = generate_webhook_secret()
                        
                        # Construct webhook URL
                        webhook_url = f"{settings.WEBHOOK_BASE_URL}/api/github/webhook-push/"
                        print(f"📌 Creating webhook at: {webhook_url}")
                        
                        # Create the webhook
                        webhook_id = await asyncio.to_thread(
                            create_webhook,
                            owner,
                            repo,
                            webhook_url,
                            webhook_secret,
                            webhook_token
                        )
                        
                        if webhook_id:
                            project.webhook_id = webhook_id
                            project.webhook_secret = webhook_secret
                            db.add(project)
                            await db.flush()
                            send_terminal_message(project_id, "✅ Auto-sync webhook configured!\n\r")
                            print(f"✅ Webhook created for project {project_id}: ID {webhook_id}")
                        else:
                            send_terminal_message(project_id, "⚠️ Could not create webhook (may need admin:repo_hook permission)\n\r")
                    else:
                        print(f"⚠️ Could not parse repo URL: {project.github_url}")
                        send_terminal_message(project_id, f"⚠️ Could not parse repo URL for webhook\n\r")
            elif project.webhook_id:
                send_terminal_message(project_id, "ℹ️ Auto-sync webhook already configured\n\r")
            elif not settings.WEBHOOK_BASE_URL:
                print("ℹ️ WEBHOOK_BASE_URL not configured, skipping webhook setup")
                send_terminal_message(project_id, "ℹ️ Webhook URL not configured, skipping auto-sync setup\n\r")

            # Step 2: Get latest version and increment
            # Query the latest build for this project to get the current version
            latest_build_result = await db.execute(
                select(ProjectBuild)
                .where(ProjectBuild.project_id == project.project_id)
                .order_by(ProjectBuild.build_id.desc())
                .limit(1)
            )
            latest_build = latest_build_result.scalars().first()
            
            # Calculate new version (increment minor version by 0.1)
            if latest_build and latest_build.build_version:
                try:
                    current_version = float(latest_build.build_version)
                    new_version = f"{current_version + 0.1:.1f}"
                except ValueError:
                    new_version = "1.0"  # Fallback if version is not a valid number
            else:
                new_version = "1.0"  # First build
            
            # Create a build record with the new version
            new_build = ProjectBuild(
                project_id=project.project_id,
                commit_id=commit_id,
                build_status=BuildStatus.queued,
                build_version=new_version
            )
            db.add(new_build)
            await db.flush()              # <-- get PK without expiring
            build_id = new_build.build_id
            

            send_terminal_message(project_id, f"Handing over to build agent...\n\r")



            # Step 3: Trigger kafka job for agent
            kafka_payload = {
                "action": 'agent-jobs',
                "project_id": str(project_id),
                "repo_url": f"https://github.com/{settings.GITHUB_ORG}/{mirror_name}.git",
                "build_id": str(build_id),
                "project_id": str(project.project_id),
                "mirror_repo_url": mirror_url,
                "commit_id": commit_id
            }

            # 5. Send message to kafka
            print(f"Sending to Kafka: {kafka_payload}")
            producer = get_kafka_producer()
            producer.send(settings.KAFKA_TOPIC_AGENT_JOBS, value=kafka_payload)
            producer.flush()
            print("Message sent to Kafka successfully")

            await db.commit()

        except Exception as e:
            send_terminal_message(project_id, f"Error during code sync: {e}")
            return
