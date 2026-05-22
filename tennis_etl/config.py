"""Environment-backed configuration for the Tennis ETL."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Runtime settings needed by the API and database layers."""

    sportradar_api_key: str
    database_url: str
    access_level: str = "trial"
    language_code: str = "en"
    http_timeout_seconds: int = 20
    http_max_retries: int = 4

    @classmethod
    def from_environment(cls) -> "Settings":
        """Read settings from environment variables and validate them."""
        api_key = os.getenv("SPORTRADAR_API_KEY")
        database_url = os.getenv("DATABASE_URL")
        missing = [
            name
            for name, value in {
                "SPORTRADAR_API_KEY": api_key,
                "DATABASE_URL": database_url,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(
                "Missing required environment variables: " + ", ".join(missing)
            )

        access_level = os.getenv("SPORTRADAR_ACCESS_LEVEL", "trial").lower()
        if access_level not in {"trial", "production"}:
            raise ValueError(
                "SPORTRADAR_ACCESS_LEVEL must be either 'trial' or 'production'."
            )

        return cls(
            sportradar_api_key=api_key or "",
            database_url=database_url or "",
            access_level=access_level,
            language_code=os.getenv("SPORTRADAR_LANGUAGE_CODE", "en"),
            http_timeout_seconds=int(os.getenv("HTTP_TIMEOUT_SECONDS", "20")),
            http_max_retries=int(os.getenv("HTTP_MAX_RETRIES", "4")),
        )
