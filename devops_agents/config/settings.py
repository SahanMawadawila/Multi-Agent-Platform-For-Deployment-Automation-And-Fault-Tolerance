# config/settings.py
import os  # Import os to access operating system environment variables
from dotenv import load_dotenv  # Import load_dotenv to read .env files
from pydantic import BaseModel, Field  # Import Pydantic for strict data validation

# Load environment variables from a .env file into the system environment
load_dotenv()

class Settings(BaseModel):
    """
    Centralized configuration management.
    Validates that all required variables exist at startup.
    """
    # OpenAI API Key for the LLM
    openai_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    # GitHub Token for cloning private repos
    github_token: str = Field(default_factory=lambda: os.getenv("GITHUB_TOKEN"))
    # GitHub Organization name
    github_org: str = Field(default_factory=lambda: os.getenv("GITHUB_ORG"))
    # Kafka bootstrap server address
    kafka_server: str = Field(default="localhost:9092")
    # Kafka topic to listen to
    kafka_topic: str = Field(default="agent-jobs")

    langchain_api_key: str = Field(default_factory=lambda: os.getenv("LANGCHAIN_API_KEY"))

    def validate_keys(self):
        """Checks if critical keys are missing and raises an error if so."""
        if not self.openai_key:
            # Raise error immediately if API key is missing
            raise ValueError("Missing OPENAI_API_KEY in .env")
        if not self.github_token:
            # Raise error immediately if GitHub token is missing
            raise ValueError("Missing GITHUB_TOKEN in .env")
        if os.getenv("LANGCHAIN_TRACING_V2") == "true" and not self.langchain_api_key:
            raise ValueError("Tracing is enabled (LANGCHAIN_TRACING_V2=true) but LANGCHAIN_API_KEY is missing.")

# Instantiate the settings object to be imported elsewhere
settings = Settings()
# Run validation immediately
settings.validate_keys()