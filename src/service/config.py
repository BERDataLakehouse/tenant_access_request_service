"""
Configuration settings for the Tenant Access Request Service.

A service for handling tenant access requests with Slack-based approval workflow.
"""

import logging
import os
from functools import lru_cache

from pydantic import BaseModel, Field

APP_VERSION = "0.1.0"


class Settings(BaseModel):
    """
    Application settings for the Tenant Access Request Service.
    """

    app_name: str = "Tenant Access Request Service"
    app_description: str = (
        "FastAPI service for tenant access requests with Slack approval workflow"
    )
    api_version: str = APP_VERSION
    log_level: str = Field(
        default=os.getenv("LOG_LEVEL", "INFO"),
        description="Logging level for the application",
    )

    # Slack configuration
    slack_bot_token: str = Field(
        default=os.getenv("SLACK_BOT_TOKEN", ""),
        description="Slack Bot OAuth Token (xoxb-...)",
    )
    slack_signing_secret: str = Field(
        default=os.getenv("SLACK_SIGNING_SECRET", ""),
        description="Slack Signing Secret for request verification",
    )
    slack_channel_id: str = Field(
        default=os.getenv("SLACK_CHANNEL_ID", ""),
        description="Slack Channel ID for approval messages",
    )

    # Governance API configuration
    governance_api_url: str = Field(
        default=os.getenv("GOVERNANCE_API_URL", ""),
        description="URL of the minio_manager_service governance API",
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get the application settings.

    Uses lru_cache to avoid loading the settings for every request.
    """
    return Settings()


# Global settings instance for convenience
settings = get_settings()


def configure_logging():
    """Configure logging for the application."""
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if settings.log_level.upper() not in logging.getLevelNamesMapping():
        logging.warning(
            "Unrecognized log level '%s'. Falling back to 'INFO'.",
            settings.log_level,
        )
