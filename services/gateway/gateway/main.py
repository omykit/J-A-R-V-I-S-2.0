"""JARVIS Gateway — FastAPI application."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import settings
from .reminders import poll_reminders_loop, pop_pending
from .router import check_services_health, route_text

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(poll_reminders_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="JARVIS Gateway", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GatewayRequest(BaseModel):
    text: str
    chat_history: list[dict[str, str]] = Field(default_factory=list)
    selected_action: str = "chrome"
    last_action: str = "chrome"
    owner_name: str = ""


class GatewayResponse(BaseModel):
    source: str  # "command", "ai", "fallback"
    spoken_text: str
    full_text: str = ""
    action: str | None = None
    action_target: str | None = None
    action_data: dict | None = None
    focus_text: str | None = None
    model_used: str | None = None


class HealthResponse(BaseModel):
    status: str
    services: dict[str, Any] = Field(default_factory=dict)


@app.get("/health", response_model=HealthResponse)
async def health():
    services = await check_services_health()
    all_ok = all(s.get("status") == "ok" for s in services.values())
    return HealthResponse(
        status="ok" if all_ok else "degraded",
        services=services,
    )


@app.post("/chat", response_model=GatewayResponse)
async def chat(body: GatewayRequest):
    result = await route_text(
        body.text,
        chat_history=body.chat_history,
        selected_action=body.selected_action,
        last_action=body.last_action,
        owner_name=body.owner_name,
    )
    return GatewayResponse(**result)


@app.get("/reminders/pending")
async def reminders_pending() -> dict[str, Any]:
    """Return and clear reminders that fired since the last poll.

    Backed by a background poller that checks memory-service's
    /reminders/check on an interval — see reminders.py.
    """
    return {"reminders": pop_pending()}
