"""Request routing: text -> command-service -> (if unmatched) -> ai-service."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from .config import settings

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = 30.0


async def route_text(
    text: str,
    *,
    chat_history: list[dict[str, str]] | None = None,
    selected_action: str = "chrome",
    last_action: str = "chrome",
    owner_name: str = "",
) -> dict[str, Any]:
    """Route user text through command-service, then ai-service if unmatched."""
    # Step 1: Try command service
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            cmd_response = await client.post(
                f"{settings.command_service_url}/execute",
                json={
                    "text": text,
                    "selected_action": selected_action,
                    "last_action": last_action,
                },
            )
            if cmd_response.status_code == 200:
                result = cmd_response.json()
                if result.get("handled") and result.get("action") != "ai_fallback":
                    return {
                        "source": "command",
                        "spoken_text": result.get("response", ""),
                        "full_text": result.get("full_response") or result.get("response", ""),
                        "action": result.get("action"),
                        "action_target": result.get("action_target"),
                        "action_data": result.get("action_data"),
                        "focus_text": result.get("focus_text"),
                    }
    except Exception as exc:
        logger.error(f"Command service error: {exc}")

    # Step 2: Fall back to AI service
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            ai_response = await client.post(
                f"{settings.ai_service_url}/chat",
                json={
                    "text": text,
                    "chat_history": chat_history or [],
                    "owner_name": owner_name,
                },
            )
            if ai_response.status_code == 200:
                result = ai_response.json()
                return {
                    "source": "ai",
                    "spoken_text": result.get("spoken_text", ""),
                    "full_text": result.get("full_text", ""),
                    "model_used": result.get("model_used", ""),
                }
    except Exception as exc:
        logger.error(f"AI service error: {exc}")

    return {
        "source": "fallback",
        "spoken_text": "I'm having trouble processing that request right now.",
        "full_text": "Service communication error.",
    }


async def check_services_health() -> dict[str, Any]:
    """Check health of all downstream services."""
    statuses: dict[str, Any] = {}
    for name, url in [
        ("memory", settings.memory_service_url),
        ("ai", settings.ai_service_url),
        ("command", settings.command_service_url),
    ]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{url}/health")
                statuses[name] = response.json() if response.status_code == 200 else {"status": "error", "detail": f"HTTP {response.status_code}"}
        except Exception as exc:
            statuses[name] = {"status": "unreachable", "detail": str(exc)}
    return statuses
