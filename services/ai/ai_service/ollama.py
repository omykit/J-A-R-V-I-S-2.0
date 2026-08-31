"""Ollama health checking and connection utilities."""
from __future__ import annotations

import json
import logging
import time
import urllib.request
from dataclasses import dataclass, field
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)

FALLBACK_MODELS = ["llama3", "phi3"]
MAX_TIMEOUT_SECONDS = 45
DEFAULT_TIMEOUT_SECONDS = 9

# Cap for the health probe specifically. It was hardcoded at 3.0, which is
# too tight: a busy Ollama loading a model under GPU pressure can exceed it,
# be declared dead, and send every turn to the fallback string without ever
# calling Ollama. Still a cap rather than an unbounded wait, and still well
# under settings.timeout_seconds (30) so a probe can never outlast a request.
#
# This would NOT have prevented the 2026-08-31 outage: Ollama was not running
# at all, and connection-refused returns in ~5ms. It guards the other
# failure -- Ollama alive but slow.
HEALTH_CHECK_TIMEOUT_SECONDS = 8.0
MAX_RETRIES = 1
RETRY_DELAY_SECONDS = 0.7
BACKGROUND_STREAM_TIMEOUT_SECONDS = 60


@dataclass
class OllamaHealth:
    checked_at: float
    available: bool
    models: set[str] = field(default_factory=set)
    error: str = ""
    degraded: bool = False


def ollama_root_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    path = parsed.path.rstrip("/")
    if path.endswith("/v1"):
        path = path[:-3]
    return urlunparse((parsed.scheme, parsed.netloc, path.rstrip("/"), "", "", "")).rstrip("/")


def model_names_from_tags(data: dict) -> set[str]:
    names: set[str] = set()
    models = data.get("models", [])
    if not isinstance(models, list):
        return names
    for model in models:
        if not isinstance(model, dict):
            continue
        name = str(model.get("name") or model.get("model") or "").strip()
        if name:
            names.add(name)
            names.add(name.split(":", 1)[0])
    return names


def should_use_ollama_native_chat(base_url: str) -> bool:
    parsed = urlparse(base_url)
    host = (parsed.hostname or "").casefold()
    return host in {"localhost", "127.0.0.1"} and (parsed.port in {11434, None})


def ollama_chat_url(base_url: str) -> str:
    return f"{ollama_root_url(base_url)}/api/chat"


def check_ollama_health(base_url: str, timeout_seconds: float) -> OllamaHealth:
    root_url = ollama_root_url(base_url)
    tags_url = f"{root_url}/api/tags"
    request = urllib.request.Request(tags_url, headers={"Accept": "application/json"})
    started_at = time.perf_counter()
    try:
        with urllib.request.urlopen(
            request, timeout=min(timeout_seconds, HEALTH_CHECK_TIMEOUT_SECONDS)
        ) as response:
            data = json.loads(response.read().decode("utf-8"))
        models = model_names_from_tags(data)
        health = OllamaHealth(
            checked_at=time.perf_counter(),
            available=bool(models),
            models=models,
            error="" if models else "No Ollama models installed",
            degraded=not bool(models),
        )
        elapsed = time.perf_counter() - started_at
        if models:
            logger.info(f"Health check OK in {elapsed:.2f}s models={','.join(sorted(health.models))}")
        else:
            logger.error(f"Ollama is running but no models are installed ({elapsed:.2f}s)")
    except Exception as exc:
        health = OllamaHealth(
            checked_at=time.perf_counter(),
            available=False,
            models=set(),
            error=str(exc),
            degraded=True,
        )
        logger.error(f"Ollama health check failed: {exc}")
    return health


def candidate_models(primary_model: str, available_models: set[str]) -> list[str]:
    candidates: list[str] = []
    for model in [primary_model, *FALLBACK_MODELS]:
        model = str(model or "").strip()
        if model and model not in candidates:
            candidates.append(model)
    if not available_models:
        return candidates
    filtered = [
        model
        for model in candidates
        if model in available_models or model.split(":", 1)[0] in available_models
    ]
    return filtered or candidates
