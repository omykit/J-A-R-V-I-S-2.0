"""Memory service configuration."""
from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://jarvis:changeme@localhost:5432/jarvis"
    echo_sql: bool = False
    # Whether to require a TLS-verified connection (NeonDB requires TLS). Set
    # to false only for a local Postgres that doesn't have SSL configured.
    db_ssl: bool = True

    # extra="ignore": the repo uses one shared root .env for all four
    # services (JARVIS_MEMORY_*, JARVIS_AI_*, JARVIS_CMD_*, JARVIS_GW_*).
    # Without this, pydantic-settings' dotenv loader raises extra_forbidden
    # for every other service's vars when this Settings model reads the file
    # directly (uvicorn/pytest run locally). Docker is unaffected — each
    # container only ever receives its own explicit environment: block.
    model_config = {"env_prefix": "JARVIS_MEMORY_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
