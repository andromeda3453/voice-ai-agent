"""Application configuration settings."""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    app_name: str = "Voice AI Patient Registration API"
    environment: str = "development"
    port: int = 8000
    log_level: str = "INFO"

    # Database
    database_url: str = "sqlite:///./patients.db"

    # Vapi Integration
    vapi_api_key: str = ""
    vapi_server_secret: str = ""
    llm_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
