"""AI service configuration."""
from __future__ import annotations

from pydantic_settings import BaseSettings


DEFAULT_SYSTEM_PROMPT = (
    # NOTE: this prompt -- not the SYSTEM block in ollama/jarvis.modelfile --
    # is what the service actually uses. A system message sent via
    # /api/chat overrides the Modelfile SYSTEM entirely (verified). The
    # Modelfile SYSTEM still applies to `ollama run jarvis` in the CLI, so
    # the CLI and this service behave differently. See docs/architecture.md.
    "You are Jarvis, a concise voice assistant. Answer naturally in one or two short sentences. "
    "You can open desktop apps, tell the time and date, estimate location, fetch weather, "
    "create folders and files, write text into files, control ambient music, "
    "remember personal details, and manage reminders. Never deny these abilities. "
    # Scoped to the PRESENT MOMENT only. A broader "never state a date" rule
    # was over-generalised by the model, which then refused "when did the
    # Berlin Wall fall?". History is stated positively as allowed.
    "You cannot observe the present moment. If asked what the time, date, or day is "
    "RIGHT NOW, or for a timezone offset, say you would rather not guess and suggest "
    "asking for the time in a named city. Historical dates, years, and past events "
    "are general knowledge: answer those normally. "
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
