"""HTTP client for communicating with the JARVIS Gateway."""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8080")


@dataclass
class GatewayResponse:
    source: str = "fallback"
    spoken_text: str = ""
    full_text: str = ""
    action: str | None = None
    action_target: str | None = None
    action_data: dict | None = None
    focus_text: str | None = None
    model_used: str | None = None
    error: str = ""


def send_chat(
    text: str,
    *,
    chat_history: list[dict[str, str]] | None = None,
    selected_action: str = "chrome",
    last_action: str = "chrome",
    owner_name: str = "",
) -> GatewayResponse:
    """Send a chat request to the gateway and return the response."""
    url = f"{GATEWAY_URL.rstrip('/')}/chat"
    payload = json.dumps({
        "text": text,
        "chat_history": chat_history or [],
        "selected_action": selected_action,
        "last_action": last_action,
        "owner_name": owner_name,
    }).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
        return GatewayResponse(
            source=data.get("source", "fallback"),
            spoken_text=data.get("spoken_text", ""),
            full_text=data.get("full_text", ""),
            action=data.get("action"),
            action_target=data.get("action_target"),
            action_data=data.get("action_data"),
            focus_text=data.get("focus_text"),
            model_used=data.get("model_used"),
        )
    except urllib.error.HTTPError as exc:
        logger.error(f"Gateway HTTP error: {exc.code}")
        return GatewayResponse(error=f"HTTP {exc.code}")
    except Exception as exc:
        logger.error(f"Gateway request failed: {exc}")
        return GatewayResponse(error=str(exc))


def check_gateway_health() -> dict[str, Any]:
    """Check if the gateway is reachable and return service health."""
    url = f"{GATEWAY_URL.rstrip('/')}/health"
    try:
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"status": "unreachable", "detail": str(exc)}
