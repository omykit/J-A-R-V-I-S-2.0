"""AI service configuration."""
from __future__ import annotations

from pydantic_settings import BaseSettings


DEFAULT_SYSTEM_PROMPT = (
    "You are Jarvis, a concise voice assistant. Answer naturally in one or two short sentences. "
    "Never claim an external action has been completed unless the application or tool explicitly reports success. "
    "Never claim an email was sent, an email reminder was scheduled, or an email notification was delivered unless a real email subsystem confirms it. "
    "Jarvis currently supports local spoken reminders, not email delivery."
)


class Settings(BaseSettings):
    ollama_base_url: str = "http://localhost:11434"
    model: str = "jarvis"
    api_key: str = "ollama"
    timeout_seconds: int = 30
    max_tokens: int = 160
    max_history_messages: int = 12
    memory_service_url: str = "http://localhost:8001"
    system_prompt: str = DEFAULT_SYSTEM_PROMPT

    # extra="ignore": see services/memory/memory_service/config.py for why
    # (shared root .env across all four services).
    model_config = {"env_prefix": "JARVIS_AI_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
