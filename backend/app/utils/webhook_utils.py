"""
Webhook management utilities for GitHub repository sync.
Handles creation, deletion, and verification of webhooks.
"""
import hmac
import hashlib
import secrets
import requests
from typing import Optional, Tuple
from urllib.parse import urlparse


def generate_webhook_secret() -> str:
    """Generate a secure random secret for webhook verification."""
    return secrets.token_hex(32)


def verify_webhook_signature(payload_body: bytes, signature_header: str, secret: str) -> bool:
    """
    Verify the GitHub webhook signature.
    
    Args:
        payload_body: Raw request body bytes
        signature_header: X-Hub-Signature-256 header value (e.g., "sha256=abc123...")
        secret: The webhook secret used when creating the webhook
    
    Returns:
        True if signature is valid, False otherwise
    """
    if not signature_header:
        return False
    
    try:
        # GitHub sends signature as "sha256=<hex_digest>"
        if not signature_header.startswith("sha256="):
            return False
        
        expected_signature = signature_header[7:]  # Remove "sha256=" prefix
        
        # Compute HMAC-SHA256
        mac = hmac.new(secret.encode(), payload_body, hashlib.sha256)
        computed_signature = mac.hexdigest()
        
        # Use compare_digest to prevent timing attacks
        return hmac.compare_digest(computed_signature, expected_signature)
    except Exception:
        return False


def parse_repo_from_url(repo_url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract owner and repo name from a GitHub URL.
    
    Args:
        repo_url: GitHub URL (e.g., "https://github.com/owner/repo.git")
    
    Returns:
        Tuple of (owner, repo_name) or (None, None) if parsing fails
    """
    try:
        # Handle various URL formats
        url = repo_url.strip()
        
        # Remove .git suffix if present
        if url.endswith(".git"):
            url = url[:-4]
        
        # Parse the URL
        if url.startswith("git@github.com:"):
            # SSH format: git@github.com:owner/repo
            path = url.replace("git@github.com:", "")
        else:
            # HTTPS format
            parsed = urlparse(url)
            path = parsed.path.strip("/")
        
        parts = path.split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]
        
        return None, None
    except Exception:
        return None, None


def create_webhook(
    owner: str,
    repo: str,
    webhook_url: str,
    webhook_secret: str,
    access_token: str,
    events: list = None
) -> Optional[int]:
    """
    Create a webhook on a GitHub repository.
    
    Args:
        owner: Repository owner (user or org)
        repo: Repository name
        webhook_url: URL that will receive webhook events
        webhook_secret: Secret for signing webhook payloads
        access_token: GitHub access token with admin:repo_hook scope
        events: List of events to subscribe to (default: ["push"])
    
    Returns:
        Webhook ID if successful, None otherwise
    """
    if events is None:
        events = ["push"]
    
    url = f"https://api.github.com/repos/{owner}/{repo}/hooks"
    
    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    payload = {
        "name": "web",
        "active": True,
        "events": events,
        "config": {
            "url": webhook_url,
            "content_type": "json",
            "secret": webhook_secret,
            "insecure_ssl": "0"  # Always verify SSL
        }
    }
    
    try:
        print(f"📡 Creating webhook: POST {url}")
        print(f"📡 Webhook target URL: {webhook_url}")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 201:
            webhook_data = response.json()
            print(f"✅ Webhook created successfully: ID {webhook_data['id']}")
            return webhook_data["id"]
        elif response.status_code == 422:
            # Webhook might already exist or validation error
            error_data = response.json()
            print(f"⚠️ Webhook 422 error: {error_data}")
            # Check if it's a "Hook already exists" error
            errors = error_data.get("errors", [])
            for err in errors:
                if "already exists" in str(err.get("message", "")):
                    print("ℹ️ Webhook already exists on this repo")
            return None
        elif response.status_code == 404:
            print(f"❌ Repository not found or no access: {owner}/{repo}")
            print(f"❌ Response: {response.text}")
            return None
        elif response.status_code == 401:
            print(f"❌ Authentication failed - token may be invalid or expired")
            print(f"❌ Response: {response.text}")
            return None
        elif response.status_code == 403:
            print(f"❌ Forbidden - token lacks admin:repo_hook scope or repo access")
            print(f"❌ Response: {response.text}")
            return None
        else:
            print(f"❌ Failed to create webhook: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error creating webhook: {e}")
        return None


def delete_webhook(
    owner: str,
    repo: str,
    webhook_id: int,
    access_token: str
) -> bool:
    """
    Delete a webhook from a GitHub repository.
    
    Args:
        owner: Repository owner
        repo: Repository name
        webhook_id: ID of the webhook to delete
        access_token: GitHub access token
    
    Returns:
        True if successful, False otherwise
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/hooks/{webhook_id}"
    
    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.delete(url, headers=headers, timeout=30)
        return response.status_code == 204
    except Exception:
        return False


def list_webhooks(
    owner: str,
    repo: str,
    access_token: str
) -> list:
    """
    List all webhooks on a repository.
    
    Args:
        owner: Repository owner
        repo: Repository name
        access_token: GitHub access token
    
    Returns:
        List of webhook objects
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/hooks"
    
    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception:
        return []
