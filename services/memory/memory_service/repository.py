"""Database CRUD operations for the memory service."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Config, Conversation, Memory, Reminder


# ── Memories ──

async def get_all_memories(session: AsyncSession) -> list[Memory]:
    result = await session.execute(select(Memory).order_by(Memory.key))
    return list(result.scalars().all())


async def get_memory(session: AsyncSession, key: str) -> Memory | None:
    result = await session.execute(select(Memory).where(Memory.key == key))
    return result.scalar_one_or_none()


async def upsert_memory(session: AsyncSession, key: str, value) -> Memory:
    existing = await get_memory(session, key)
    if existing:
        existing.value = value
        existing.updated_at = datetime.now(timezone.utc)
    else:
        existing = Memory(key=key, value=value)
        session.add(existing)
    await session.commit()
    await session.refresh(existing)
    return existing


# ── Reminders ──

async def list_reminders(
    session: AsyncSession, *, include_triggered: bool = False
) -> list[Reminder]:
    query = select(Reminder).order_by(Reminder.scheduled_at)
    if not include_triggered:
        query = query.where(Reminder.triggered == False)  # noqa: E712
    result = await session.execute(query)
    return list(result.scalars().all())


async def create_reminder(
    session: AsyncSession, *, reminder_id: str, text: str, scheduled_at: datetime
) -> Reminder:
    reminder = Reminder(id=reminder_id, text=text, scheduled_at=scheduled_at)
    session.add(reminder)
    await session.commit()
    await session.refresh(reminder)
    return reminder


async def check_reminders(session: AsyncSession) -> list[Reminder]:
    now = datetime.now(timezone.utc)
    query = select(Reminder).where(
        Reminder.triggered == False, Reminder.scheduled_at <= now  # noqa: E712
    )
    result = await session.execute(query)
    due = list(result.scalars().all())
    if due:
        ids = [r.id for r in due]
        await session.execute(
            update(Reminder)
            .where(Reminder.id.in_(ids))
            .values(triggered=True, triggered_at=now)
        )
        await session.commit()
        # Refresh to get updated values
        for r in due:
            r.triggered = True
            r.triggered_at = now
    return due


# ── Config ──

async def get_config(session: AsyncSession, key: str) -> Config | None:
    result = await session.execute(select(Config).where(Config.key == key))
    return result.scalar_one_or_none()


async def get_all_config(session: AsyncSession) -> list[Config]:
    result = await session.execute(select(Config).order_by(Config.key))
    return list(result.scalars().all())


async def upsert_config(session: AsyncSession, key: str, value) -> Config:
    existing = await get_config(session, key)
    if existing:
        existing.value = value
        existing.updated_at = datetime.now(timezone.utc)
    else:
        existing = Config(key=key, value=value)
        session.add(existing)
    await session.commit()
    await session.refresh(existing)
    return existing


# ── Conversations ──

async def add_conversation(
    session: AsyncSession,
    *,
    role: str,
    content: str,
    source: str | None = None,
    session_id: str | None = None,
) -> Conversation:
    entry = Conversation(role=role, content=content, source=source, session_id=session_id)
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


async def get_recent_conversations(
    session: AsyncSession, *, limit: int = 20, session_id: str | None = None
) -> list[Conversation]:
    query = select(Conversation)
    if session_id:
        query = query.where(Conversation.session_id == session_id)
    query = (
        query
        .order_by(Conversation.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(query)
    rows = list(result.scalars().all())
    rows.reverse()  # Return in chronological order
    return rows
