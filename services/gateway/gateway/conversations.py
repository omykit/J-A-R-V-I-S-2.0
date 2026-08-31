"""Persist conversation turns to memory-service.

memory-service has had a working POST /conversations since the migration,
but nothing ever called it, so the Neon `conversations` table stayed empty
while every turn was answered and thrown away. This module is the missing
caller.

Two design points worth keeping:

  Fire-and-forget. Logging must never delay a spoken reply or fail a turn.
  Every write is dispatched as a background task and every error is
  swallowed into a warning -- if Neon is unreachable the user still gets
  their answer, they just lose the transcript for that turn.

  Written from the gateway, not the router. gateway/main.py's /chat handler
  is the one place that sees the user's text and the final answer together,
  for every turn, from both the voice and text clients. router.py returns
  early from two separate branches and would have to be restructured.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from .config import settings

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = 10.0

# Which answering paths get persisted. Currently AI turns only, which is why
# `source` is constant in the table today. Deterministic command turns ("what
# time is it", "open chrome") are high-volume and low-value as training data.
# Widen by adding "command" and "fallback" here -- no schema change needed.
LOGGED_SOURCES = frozenset({"ai"})


async def _post_turn(role: str, content: str, source: str, session_id: str) -> None:
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        response = await client.post(
            f"{settings.memory_service_url}/conversations",
            json={
                "role": role,
                "content": content,
                "source": source,
                "session_id": session_id,
            },
        )
        if response.status_code != 201:
            logger.warning(
                "conversation_log_rejected role=%s status=%s", role, response.status_code
            )


async def log_turn(
    *, user_text: str, result: dict[str, Any], session_id: str = ""
) -> bool:
    """Write one user/assistant pair. Returns whether anything was written.

    The two rows are written sequentially, not concurrently: created_at is
    what orders a transcript, and concurrent inserts can land on the same
    timestamp and read back with the answer before the question.
    """
    source = str(result.get("source") or "")
    if source not in LOGGED_SOURCES:
        return False

    assistant_text = str(result.get("full_text") or result.get("spoken_text") or "")
    if not user_text.strip() and not assistant_text.strip():
        return False

    try:
        await _post_turn("user", user_text, source, session_id)
        await _post_turn("assistant", assistant_text, source, session_id)
        return True
    except Exception as exc:
        # Never propagate: a logging failure must not break a live turn.
        logger.warning("conversation_log_failed source=%s error=%s: %s", source, type(exc).__name__, exc)
        return False


# Writes are funnelled through one queue drained by a single worker.
#
# The obvious implementation -- create_task per turn -- reorders the
# transcript, and it did so on the very first live run: two questions asked
# back to back stored as user(Q1), user(Q2), assistant(A1), assistant(A2).
# Sequential writes inside one turn are not enough, because consecutive
# turns overlap. Serialising every write in submission order is what keeps a
# transcript readable, and it costs nothing: the caller still never waits.
_queue: asyncio.Queue | None = None
_worker: asyncio.Task | None = None
_worker_loop: asyncio.AbstractEventLoop | None = None


async def _drain_forever() -> None:
    assert _queue is not None
    while True:
        job = await _queue.get()
        try:
            await log_turn(**job)
        except Exception as exc:  # pragma: no cover - log_turn already guards
            logger.warning("conversation_log_worker_error error=%s", exc)
        finally:
            _queue.task_done()


def _ensure_worker() -> asyncio.Queue:
    global _queue, _worker, _worker_loop
    loop = asyncio.get_running_loop()
    # A queue and task belong to the loop that created them; tests run each
    # case on a fresh loop, so rebuild when the loop changes.
    if _worker_loop is not loop:
        _queue = asyncio.Queue()
        _worker = None
        _worker_loop = loop
    if _worker is None or _worker.done():
        _worker = asyncio.create_task(_drain_forever())
    assert _queue is not None
    return _queue


def log_turn_in_background(
    *, user_text: str, result: dict[str, Any], session_id: str = ""
) -> None:
    """Queue a turn for writing without making the caller wait for Neon."""
    _ensure_worker().put_nowait(
        {"user_text": user_text, "result": result, "session_id": session_id}
    )


async def wait_until_drained() -> None:
    """Block until queued writes have been attempted (tests and shutdown)."""
    if _queue is not None:
        await _queue.join()
