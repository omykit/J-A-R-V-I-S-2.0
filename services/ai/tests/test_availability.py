"""Health-check timeout, and how an Ollama outage is surfaced.

Grounded in a real incident on 2026-08-31: Ollama's own server log shows no
listener until 15:48:04, while JARVIS was being used from 15:43. Every turn
took the unavailable branch and was answered without Ollama ever being
called, and nothing in the spoken reply said so.
"""

import logging

from ai_service import completion
from ai_service.completion import (
    SERVICE_UNAVAILABLE_SPOKEN,
    fallback_response,
    get_ai_response,
    service_unavailable_response,
)
from ai_service.ollama import HEALTH_CHECK_TIMEOUT_SECONDS, OllamaHealth, check_ollama_health


def unavailable_health(error: str = "<urlopen error [Errno 111] Connection refused>"):
    return OllamaHealth(checked_at=0.0, available=False, models=set(), error=error, degraded=True)


# ── Task 1: the health-probe timeout cap ────────────────────────────────


def test_the_health_probe_cap_is_no_longer_three_seconds():
    """3.0 was too tight for a busy Ollama loading a model."""
    assert HEALTH_CHECK_TIMEOUT_SECONDS > 3.0


def test_the_probe_stays_capped_below_the_request_timeout():
    """It must remain a cap, not an unbounded wait, and a probe must never
    be able to outlast the request it gates."""
    from ai_service.config import settings

    assert HEALTH_CHECK_TIMEOUT_SECONDS <= 10.0
    assert HEALTH_CHECK_TIMEOUT_SECONDS < settings.timeout_seconds


def test_an_unreachable_ollama_still_fails_fast(monkeypatch):
    """Raising the cap must not slow down the genuinely-down case. A refused
    connection returns immediately; only a hanging one reaches the cap."""
    import urllib.request

    def refuse(*args, **kwargs):
        raise OSError("[Errno 111] Connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", refuse)

    health = check_ollama_health("http://host.docker.internal:11434", 30)

    assert health.available is False
    assert health.degraded is True
    assert "Connection refused" in health.error


def test_the_smaller_of_the_two_timeouts_wins(monkeypatch):
    """A caller passing a tiny timeout must not be overridden upward."""
    captured = {}

    import urllib.request

    def capture(request, timeout=None):
        captured["timeout"] = timeout
        raise OSError("stop here")

    monkeypatch.setattr(urllib.request, "urlopen", capture)
    check_ollama_health("http://x:11434", 1.0)

    assert captured["timeout"] == 1.0


# ── Task 4: making degradation loud ─────────────────────────────────────


def test_an_outage_reply_names_the_cause():
    """A service outage must be distinguishable from a bad answer by ear."""
    response = service_unavailable_response(error="boom")

    assert "language model" in response.spoken_text.lower()
    assert response.spoken_text == SERVICE_UNAVAILABLE_SPOKEN


def test_the_outage_reply_is_not_the_generic_fallback():
    """The generic "I couldn't generate a response" is what let a real
    four-minute outage sound like ordinary unhelpfulness."""
    generic = {fallback_response() for _ in range(50)}

    assert SERVICE_UNAVAILABLE_SPOKEN not in generic


def test_get_ai_response_returns_the_outage_reply_when_unavailable():
    result = get_ai_response("what is docker", health=unavailable_health())

    assert result.spoken_text == SERVICE_UNAVAILABLE_SPOKEN
    assert "Connection refused" in result.error


def test_the_outage_is_logged_at_error_with_the_reason(caplog):
    """Warning is not enough -- this is an outage, and it was invisible."""
    with caplog.at_level(logging.ERROR, logger=completion.__name__):
        get_ai_response("what is docker", health=unavailable_health())

    assert "AI_UNAVAILABLE" in caplog.text
    assert "Connection refused" in caplog.text
    assert any(record.levelno >= logging.ERROR for record in caplog.records)


def test_ollama_is_never_called_on_the_unavailable_path(monkeypatch):
    """Pins the existing short-circuit: no request is attempted at all."""
    def explode(*args, **kwargs):
        raise AssertionError("Ollama was called despite unavailable health")

    monkeypatch.setattr(completion, "_request_ollama_native", explode)

    result = get_ai_response("what is docker", health=unavailable_health())

    assert result.spoken_text == SERVICE_UNAVAILABLE_SPOKEN
