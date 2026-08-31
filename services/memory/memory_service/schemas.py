"""Pydantic schemas for the memory service API."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Memories ──

class MemoryCreate(BaseModel):
    key: str
    value: Any


class MemoryResponse(BaseModel):
    key: str
    value: Any
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Reminders ──

class ReminderCreate(BaseModel):
    text: str
    scheduled_at: datetime


class ReminderResponse(BaseModel):
    id: str
    text: str
    scheduled_at: datetime
    triggered: bool
    created_at: datetime
    triggered_at: datetime | None = None

    model_config = {"from_attributes": True}


class ReminderCheckResponse(BaseModel):
    triggered: list[ReminderResponse]


# ── Config ──

class ConfigEntry(BaseModel):
    key: str
    value: Any

    model_config = {"from_attributes": True}


# ── Conversations ──

class ConversationCreate(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    source: str | None = Field(default=None, max_length=16)
    session_id: str | None = Field(default=None, max_length=64)


class ConversationResponse(BaseModel):
    id: int
    role: str
    content: str
    source: str | None = None
    session_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Health ──

class HealthResponse(BaseModel):
    status: str
    detail: str = ""
