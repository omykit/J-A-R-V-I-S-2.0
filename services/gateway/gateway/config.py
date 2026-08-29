"""Gateway configuration."""
from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ai_service_url: str = "http://localhost:8002"
    command_service_url: str = "http://localhost:8003"
    memory_service_url: str = "http://localhost:8001"
    host: str = "0.0.0.0"
    port: int = 8080
    allowed_origins: str = "http://localhost:3000,http://localhost:19006,http://127.0.0.1:3000"

    # extra="ignore": see services/memory/memory_service/config.py for why
    # (shared root .env across all four services).
    model_config = {"env_prefix": "JARVIS_GW_", "env_file": ".env", "extra": "ignore"}

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


settings = Settings()
