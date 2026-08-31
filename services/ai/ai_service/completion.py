"""AI completion logic — streaming and non-streaming Ollama/OpenAI requests."""
from __future__ import annotations

import json
import logging
import random
import re
import time
import urllib.request
from dataclasses import dataclass, field

from openai import OpenAI

from .config import settings
from .ollama import (
    BACKGROUND_STREAM_TIMEOUT_SECONDS,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_RETRIES,
    MAX_TIMEOUT_SECONDS,
    RETRY_DELAY_SECONDS,
    OllamaHealth,
    candidate_models,
    check_ollama_health,
    ollama_chat_url,
    ollama_root_url,
    should_use_ollama_native_chat,
)
from .response_cleaner import RESPONSE_RULE_SUFFIX, clean_ai_response, clean_streaming_candidate

logger = logging.getLogger(__name__)

# Wall-clock ceiling for one get_ai_response call, retries and fallback
# models included. Must stay strictly below the gateway's HTTP_TIMEOUT,
# which must stay below the client's request timeout. See get_ai_response.
TOTAL_BUDGET_SECONDS = 25.0

_FALLBACK_RESPONSE_VARIANTS: list[str] = [
    "Apologies, I couldn't generate a response right now.",
    "I'm having trouble forming a response at the moment.",
    "I wasn't able to put something together — try again?",
    "I ran into a hiccup while thinking. Give me another shot.",
    "Something went wrong on my end. Try asking again.",
]


@dataclass
class AIResponse:
    spoken_text: str = ""
    full_text: str = ""
    error: str = ""
    model_used: str = ""


def fallback_response() -> str:
    return random.choice(_FALLBACK_RESPONSE_VARIANTS)


def fallback_ai_response(error: str = "") -> AIResponse:
    text = fallback_response()
    return AIResponse(spoken_text=text, full_text=text, error=error)


# A service outage must be distinguishable from a bad answer BY EAR. The
# generic "I couldn't generate a response" is what let a four-minute Ollama
# outage sound like ordinary unhelpfulness in session 2 -- nothing in the
# spoken reply said the language model was unreachable.
SERVICE_UNAVAILABLE_SPOKEN = (
    "I can't reach my language model right now, so I can't answer that one."
)


def service_unavailable_response(error: str = "") -> AIResponse:
    return AIResponse(
        spoken_text=SERVICE_UNAVAILABLE_SPOKEN,
        full_text=SERVICE_UNAVAILABLE_SPOKEN,
        error=error,
    )


# ── Client cache ──

_AI_CLIENT_CACHE: dict[str, OpenAI] = {}


def _get_ai_client(base_url: str, api_key: str) -> OpenAI:
    cache_key = f"{base_url}|{api_key}"
    if cache_key not in _AI_CLIENT_CACHE:
        _AI_CLIENT_CACHE[cache_key] = OpenAI(base_url=base_url, api_key=api_key)
    return _AI_CLIENT_CACHE[cache_key]


# ── Message preparation ──

def _is_detail_request(text: str) -> bool:
    lowered = text.casefold()
    markers = ("explain", "detail", "elaborate", "go deeper", "tell me more", "describe", "how does")
    return any(marker in lowered for marker in markers)


def _requested_max_tokens(text: str, default: int) -> int:
    return min(default * 3, 480) if _is_detail_request(text) else default


def _trim_history(history: list[dict], max_messages: int) -> list[dict]:
    if len(history) <= max_messages:
        return list(history)
    return list(history[-max_messages:])


def build_memory_context(memories: list[dict]) -> str:
    if not memories:
        return ""
    parts: list[str] = []
    for mem in memories:
        key = mem.get("key", "")
        value = mem.get("value", "")
        if key and value:
            parts.append(f"- {key}: {value}")
    if not parts:
        return ""
    return "Known facts about the user:\n" + "\n".join(parts)


def prepare_messages(
    text: str,
    *,
    system_prompt: str,
    chat_history: list[dict],
    memory_context: str,
    owner_name: str,
    max_history: int,
) -> list[dict]:
    full_system = system_prompt
    if owner_name:
        full_system = full_system.replace("the user", owner_name).replace("The user", owner_name)
        full_system += f"\nThe user's name is {owner_name}."
    if memory_context:
        full_system += f"\n\n{memory_context}"
    full_system += f"\n\n{RESPONSE_RULE_SUFFIX}"

    messages: list[dict] = [{"role": "system", "content": full_system}]
    messages.extend(_trim_history(chat_history, max_history))
    messages.append({"role": "user", "content": text})
    return messages


# ── Ollama native streaming ──

def _request_ollama_native(
    *,
    messages: list[dict],
    model: str,
    base_url: str,
    max_tokens: int,
    timeout: int,
) -> AIResponse:
    url = ollama_chat_url(base_url)
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"num_predict": max_tokens},
    }).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        raw = data.get("message", {}).get("content", "")
        cleaned = clean_ai_response(raw)
        return AIResponse(
            spoken_text=cleaned or fallback_response(),
            full_text=raw,
            model_used=model,
        )
    except Exception as exc:
        logger.error(f"Ollama native request failed: {exc}")
        return AIResponse(error=str(exc))


# ── OpenAI-compatible streaming ──

def _request_openai_streaming(
    *,
    messages: list[dict],
    model: str,
    base_url: str,
    api_key: str,
    max_tokens: int,
    timeout: int,
) -> AIResponse:
    openai_url = base_url
    if not openai_url.rstrip("/").endswith("/v1"):
        openai_url = f"{ollama_root_url(base_url)}/v1"

    client = _get_ai_client(openai_url, api_key)
    try:
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            stream=True,
            timeout=timeout,
        )
        full_text_parts: list[str] = []
        best_spoken = ""
        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                full_text_parts.append(delta.content)
                candidate = clean_streaming_candidate("".join(full_text_parts))
                if candidate:
                    best_spoken = candidate

        full_text = "".join(full_text_parts)
        if not best_spoken:
            best_spoken = clean_ai_response(full_text) or fallback_response()

        return AIResponse(
            spoken_text=best_spoken,
            full_text=full_text,
            model_used=model,
        )
    except Exception as exc:
        logger.error(f"OpenAI streaming failed: {exc}")
        return AIResponse(error=str(exc))


# ── Main entry point ──

def get_ai_response(
    text: str,
    *,
    chat_history: list[dict] | None = None,
    owner_name: str = "",
    memory_context: str = "",
    health: OllamaHealth | None = None,
) -> AIResponse:
    if health is None:
        health = check_ollama_health(settings.ollama_base_url, settings.timeout_seconds)

    if not health.available:
        # Error, not warning: this is an outage, and every turn taken on this
        # path is answered without Ollama ever being called.
        reason = health.error or "Ollama unavailable"
        logger.error(
            "AI_UNAVAILABLE returning service-outage reply without calling Ollama: %s",
            reason,
        )
        return service_unavailable_response(error=reason)

    max_tokens = _requested_max_tokens(text, settings.max_tokens)
    timeout = min(settings.timeout_seconds, MAX_TIMEOUT_SECONDS)

    messages = prepare_messages(
        text,
        system_prompt=settings.system_prompt,
        chat_history=chat_history or [],
        memory_context=memory_context,
        owner_name=owner_name,
        max_history=settings.max_history_messages,
    )

    models = candidate_models(settings.model, health.models)
    last_error = ""

    # A wall-clock ceiling for the WHOLE retry sequence, not per attempt.
    #
    # Without it the budget multiplies: candidate_models returns the primary
    # plus any installed fallbacks (jarvis, llama3), and each gets
    # MAX_RETRIES + 1 attempts, so 4 attempts x 30s could run ~120s. The
    # gateway gives up at HTTP_TIMEOUT and the caller is long gone, but this
    # service kept working -- burning GPU on an answer nobody will receive.
    #
    # The ladder each layer must respect, innermost first:
    #     AI total (25s)  <  gateway (35s)  <  client (45s)
    # Every layer outward must be strictly larger, or the outer one discards
    # a good answer the inner one was still producing.
    deadline = time.monotonic() + TOTAL_BUDGET_SECONDS

    for model in models:
        for attempt in range(MAX_RETRIES + 1):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                logger.error(
                    "AI_BUDGET_EXHAUSTED after %.0fs across models=%s (last_error=%s)",
                    TOTAL_BUDGET_SECONDS, models, last_error or "none",
                )
                return fallback_ai_response(
                    error=last_error or f"No answer within {TOTAL_BUDGET_SECONDS:.0f}s"
                )
            # Never let a single attempt outlive the remaining budget.
            timeout = max(1.0, min(timeout, remaining))

            use_native = should_use_ollama_native_chat(settings.ollama_base_url)
            if use_native:
                result = _request_ollama_native(
                    messages=messages,
                    model=model,
                    base_url=settings.ollama_base_url,
                    max_tokens=max_tokens,
                    timeout=timeout,
                )
            else:
                result = _request_openai_streaming(
                    messages=messages,
                    model=model,
                    base_url=settings.ollama_base_url,
                    api_key=settings.api_key,
                    max_tokens=max_tokens,
                    timeout=timeout,
                )

            if not result.error:
                return result

            last_error = result.error
            if attempt < MAX_RETRIES:
                time.sleep(min(RETRY_DELAY_SECONDS, max(0.0, deadline - time.monotonic())))

    return fallback_ai_response(error=last_error)
