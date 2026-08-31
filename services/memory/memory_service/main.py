"""JARVIS Memory Service — FastAPI application."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from . import repository as repo
from .database import engine, get_session
from .models import Base
from .schemas import (
    ConfigEntry,
    ConversationCreate,
    ConversationResponse,
    HealthResponse,
    MemoryCreate,
    MemoryResponse,
    ReminderCheckResponse,
    ReminderCreate,
    ReminderResponse,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (for development; use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="JARVIS Memory Service", version="1.0.0", lifespan=lifespan)


# Neon lookups intermittently fail inside the container with
# "socket.gaierror: [Errno -2] Name or service not known" -- a DNS blip, not
# a credentials or TLS problem. Observed 2026-08-31 18:03 UTC, where it
# escaped as an unhandled ASGI exception: POST /reminders/check returned 500
# with a full traceback. /reminders/check is polled every 30s by the
# gateway, so it is the most exposed endpoint in the service.
#
# A database blip is a temporary, retryable condition: report it as 503 with
# a short reason so callers can back off, instead of a 500 that reads like a
# bug and leaks internals. This only changes the failure shape -- successful
# requests are untouched.
@app.exception_handler(SQLAlchemyError)
async def _database_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error("DATABASE_UNAVAILABLE %s %s: %s", request.url.path, type(exc).__name__, exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Database temporarily unavailable", "error": type(exc).__name__},
    )


@app.exception_handler(OSError)
async def _network_error_handler(request: Request, exc: OSError) -> JSONResponse:
    """socket.gaierror is an OSError and can escape outside SQLAlchemy's wrapping."""
    logger.error("DATABASE_UNREACHABLE %s %s: %s", request.url.path, type(exc).__name__, exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Database temporarily unreachable", "error": type(exc).__name__},
    )


# ── Health ──

@app.get("/health", response_model=HealthResponse)
async def health(session: AsyncSession = Depends(get_session)):
    """Liveness *and* readiness: a reachable process with an unreachable
    database is not healthy. Without the query below the container reports
    healthy while Neon is down, and ai/command-service (which gate on
    condition: service_healthy) start behind that false signal."""
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content=HealthResponse(
                status="unavailable", detail=f"Database unreachable: {exc}"
            ).model_dump(),
        )
    return HealthResponse(status="ok", detail="Memory service is running")


# ── Memories ──

@app.get("/memories", response_model=list[MemoryResponse])
async def list_memories(session: AsyncSession = Depends(get_session)):
    return await repo.get_all_memories(session)


@app.get("/memories/{key}", response_model=MemoryResponse)
async def get_memory(key: str, session: AsyncSession = Depends(get_session)):
    memory = await repo.get_memory(session, key)
    if memory is None:
        raise HTTPException(status_code=404, detail=f"Memory '{key}' not found")
    return memory


@app.post("/memories", response_model=MemoryResponse, status_code=201)
async def upsert_memory(body: MemoryCreate, session: AsyncSession = Depends(get_session)):
    return await repo.upsert_memory(session, body.key, body.value)


# ── Reminders ──

@app.get("/reminders", response_model=list[ReminderResponse])
async def list_reminders(
    include_triggered: bool = False,
    session: AsyncSession = Depends(get_session),
):
    return await repo.list_reminders(session, include_triggered=include_triggered)


@app.post("/reminders", response_model=ReminderResponse, status_code=201)
async def create_reminder(body: ReminderCreate, session: AsyncSession = Depends(get_session)):
    reminder_id = f"reminder-{int(datetime.now(timezone.utc).timestamp() * 1000)}"
    return await repo.create_reminder(
        session, reminder_id=reminder_id, text=body.text, scheduled_at=body.scheduled_at
    )


@app.post("/reminders/check", response_model=ReminderCheckResponse)
async def check_reminders(session: AsyncSession = Depends(get_session)):
    triggered = await repo.check_reminders(session)
    return ReminderCheckResponse(
        triggered=[ReminderResponse.model_validate(r) for r in triggered]
    )


# ── Config ──

@app.get("/config", response_model=list[ConfigEntry])
async def list_config(session: AsyncSession = Depends(get_session)):
    return await repo.get_all_config(session)


@app.get("/config/{key}", response_model=ConfigEntry)
async def get_config(key: str, session: AsyncSession = Depends(get_session)):
    entry = await repo.get_config(session, key)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Config '{key}' not found")
    return entry


@app.put("/config/{key}", response_model=ConfigEntry)
async def upsert_config(key: str, body: ConfigEntry, session: AsyncSession = Depends(get_session)):
    return await repo.upsert_config(session, key, body.value)


# ── Conversations ──

@app.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    limit: int = 20,
    session_id: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    return await repo.get_recent_conversations(session, limit=limit, session_id=session_id)


@app.post("/conversations", response_model=ConversationResponse, status_code=201)
async def add_conversation(
    body: ConversationCreate,
    session: AsyncSession = Depends(get_session),
):
    return await repo.add_conversation(
        session,
        role=body.role,
        content=body.content,
        source=body.source,
        session_id=body.session_id,
    )
