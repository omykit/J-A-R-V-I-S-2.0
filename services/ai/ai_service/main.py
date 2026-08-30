"""JARVIS AI Service — FastAPI application."""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field

from .completion import AIResponse, build_memory_context, get_ai_response
from .config import settings
from .ollama import OllamaHealth, check_ollama_health
from .truthfulness import guard_response

logger = logging.getLogger(__name__)

# ── Module-level health state ──
_ollama_health: OllamaHealth | None = None
# /chat must not trust an arbitrarily old snapshot (e.g. one taken before a
# model was created in Ollama) — only /health used to refresh this cache, so
# a container that never gets a /health hit would stay wrong indefinitely.
HEALTH_CACHE_TTL_SECONDS = 30


def _get_fresh_health() -> OllamaHealth:
    global _ollama_health
    is_stale = (
        _ollama_health is None
        or time.perf_counter() - _ollama_health.checked_at > HEALTH_CACHE_TTL_SECONDS
    )
    if is_stale:
        _ollama_health = check_ollama_health(settings.ollama_base_url, settings.timeout_seconds)
    return _ollama_health


# ── Request/Response models ──

class ChatRequest(BaseModel):
    text: str
    chat_history: list[dict[str, str]] = Field(default_factory=list)
    owner_name: str = ""
    config: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    spoken_text: str
    full_text: str
    model_used: str = ""
    error: str = ""


class HealthResponse(BaseModel):
    status: str
    detail: str = ""
    models: list[str] = Field(default_factory=list)


# ── Lifespan ──

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _ollama_health
    _ollama_health = check_ollama_health(settings.ollama_base_url, settings.timeout_seconds)
    if _ollama_health.available:
        logger.info(f"Ollama healthy: models={sorted(_ollama_health.models)}")
    else:
        logger.warning(f"Ollama unavailable: {_ollama_health.error}")
    yield


app = FastAPI(title="JARVIS AI Service", version="1.0.0", lifespan=lifespan)


# ── Health ──

@app.get("/health", response_model=HealthResponse)
async def health():
    global _ollama_health
    _ollama_health = check_ollama_health(settings.ollama_base_url, settings.timeout_seconds)
    if _ollama_health.available:
        return HealthResponse(
            status="ok",
            detail="Ollama is available",
            models=sorted(_ollama_health.models),
        )
    return HealthResponse(
        status="degraded" if _ollama_health.degraded else "unavailable",
        detail=_ollama_health.error,
    )


# ── Fetch memories from memory service ──

async def _fetch_memories() -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.memory_service_url}/memories")
            if response.status_code == 200:
                return response.json()
    except Exception as exc:
        logger.warning(f"Failed to fetch memories: {exc}")
    return []


# ── Chat endpoint ──

@app.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest):
    # Fetch memory context from memory service
    memories = await _fetch_memories()
    memory_context = build_memory_context(memories)
    health = _get_fresh_health()

    # Get AI response (synchronous — runs in threadpool via FastAPI)
    import asyncio
    loop = asyncio.get_event_loop()
    result: AIResponse = await loop.run_in_executor(
        None,
        lambda: get_ai_response(
            body.text,
            chat_history=body.chat_history,
            owner_name=body.owner_name,
            memory_context=memory_context,
            health=health,
        ),
    )

    # The model has no clock or timezone data, so any current time/date it
    # produces is fabricated. Replace such answers with an honest refusal.
    # See truthfulness.py for why this guards the output, not the input.
    spoken_text, full_text, _blocked_rule = guard_response(
        result.spoken_text, result.full_text
    )

    return ChatResponse(
        spoken_text=spoken_text,
        full_text=full_text,
        model_used=result.model_used,
        error=result.error,
    )
