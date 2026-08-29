"""Shared Pydantic schemas used across JARVIS services."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str


class ChatRequest(BaseModel):
    text: str
    chat_history: list[ChatMessage] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    spoken_text: str
    full_text: str
    source: str = "ai"  # "ai", "command", "fallback"


class CommandResult(BaseModel):
    handled: bool
    response: str
    full_response: str | None = None
    status: str = "Jarvis Activated"
    focus_text: str | None = None
    action: str | None = None  # "launch", "music", "ai_fallback", etc.
    action_target: str | None = None  # e.g. "chrome", "play", etc.


class MemoryEntry(BaseModel):
    key: str
    value: Any
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ReminderEntry(BaseModel):
    id: str
    text: str
    scheduled_at: datetime
    triggered: bool = False
    created_at: datetime | None = None
    triggered_at: datetime | None = None


class ReminderCreate(BaseModel):
    text: str
    scheduled_at: datetime


class HealthResponse(BaseModel):
    status: str  # "ok", "degraded", "unavailable"
    detail: str = ""
    models: list[str] = Field(default_factory=list)
