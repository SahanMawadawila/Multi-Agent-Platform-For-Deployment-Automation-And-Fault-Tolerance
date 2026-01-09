# config/settings.py
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

class Settings(BaseModel):
    """
    Centralized configuration management.
    """
    # OpenAI & GitHub
    openai_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    github_token: str = Field(default_factory=lambda: os.getenv("GITHUB_TOKEN"))
    github_org: str = Field(default_factory=lambda: os.getenv("GITHUB_ORG"))
    
    # Kafka
    kafka_server: str = Field(default="localhost:9092")
    kafka_topic: str = Field(default="agent-jobs")
    
    # LangChain
    langchain_api_key: str = Field(default_factory=lambda: os.getenv("LANGCHAIN_API_KEY"))

    # AWS Credentials
    aws_access_key: str = Field(default_factory=lambda: os.getenv("AWS_ACCESS_KEY"))
    aws_secret_key: str = Field(default_factory=lambda: os.getenv("AWS_SECRET_KEY"))
    aws_region: str = Field(default="ap-south-1", description="Default bucket region")

    def validate_keys(self):
        """Checks if critical keys are missing."""
        if not self.openai_key:
            raise ValueError("Missing OPENAI_API_KEY in .env")
        if not self.github_token:
            raise ValueError("Missing GITHUB_TOKEN in .env")
        if not self.aws_access_key or not self.aws_secret_key:
            raise ValueError("Missing AWS Credentials (AWS_ACCESS_KEY or AWS_SECRET_KEY) in .env")

# Instantiate and validate
settings = Settings()
settings.validate_keys()