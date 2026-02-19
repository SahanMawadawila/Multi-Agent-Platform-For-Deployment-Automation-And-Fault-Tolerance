from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All environment variables are loaded from .env file automatically.
    """
    
    # Database settings
    DATABASE_URL: str
    
    # GitHub/Git settings
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_ORG: Optional[str] = None
    
    # Kafka settings
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_AGENT_JOBS: str = "agent-jobs"

    # Kubernetes settings
    KUBECONFIG: Optional[str] = None
    
    # Security settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 1 day
    
    # OAuth settings (if using)
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    
    # Application settings
    APP_NAME: str = "Multi-Agent Platform"
    DEBUG: bool = False
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Webhook settings
    WEBHOOK_BASE_URL: Optional[str] = "https://uncoquettishly-menstrual-frankie.ngrok-free.dev"  # e.g., https://abc123.ngrok.io (for local dev)
    GITHUB_WEBHOOK_SECRET: str = "default-webhook-secret-change-me"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"  # Allow extra env variables not defined here
    )


# Create a single instance to be imported across the app
settings = Settings()
