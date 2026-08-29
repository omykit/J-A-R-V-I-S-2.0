"""Background poller for due reminders — bridges memory-service to clients.

memory-service already knows how to find and mark due reminders
(POST /reminders/check), but nothing calls it. This module polls that
endpoint on an interval and buffers triggered reminders in memory so a
client (e.g. client/desktop_app.py) can pull them via GET /reminders/pending.

This is a stepping stone: once a client needs real-time delivery, replace
the polling here with a push (WebSocket) to connected clients instead.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from .config import settings

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 30.0

_pending: list[dict[str, Any]] = []


async def check_once() -> list[dict[str, Any]]:
    """Call memory-service /reminders/check once and buffer any triggered reminders."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{settings.memory_service_url}/reminders/check")
            if response.status_code == 200:
                triggered = response.json().get("triggered", [])
                if triggered:
                    _pending.extend(triggered)
                return triggered
    except Exception as exc:
        logger.warning(f"Reminder check failed: {exc}")
    return []


async def poll_reminders_loop(interval_seconds: float = POLL_INTERVAL_SECONDS) -> None:
    while True:
        await check_once()
        await asyncio.sleep(interval_seconds)


def pop_pending() -> list[dict[str, Any]]:
    """Return and clear all reminders buffered since the last call."""
    pending = list(_pending)
    _pending.clear()
    return pending
