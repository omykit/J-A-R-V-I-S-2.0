"""The AI service's total time budget, and the timeout ladder it belongs to.

Without a total budget the time multiplies: candidate_models returns the
primary model plus any installed fallbacks, and each gets MAX_RETRIES + 1
attempts. With jarvis and llama3 both present that is 4 attempts x 30s --
about 120s -- while the gateway gave up at 30s. The caller was long gone and
this service kept burning GPU on an answer nobody would receive.
"""

import time

from ai_service import completion
from ai_service.completion import TOTAL_BUDGET_SECONDS, AIResponse, get_ai_response
from ai_service.ollama import OllamaHealth


def healthy(models=("jarvis", "llama3")):
    return OllamaHealth(checked_at=0.0, available=True, models=set(models))


def test_the_ladder_holds_ai_below_gateway_below_client():
    """AI total (25s) < gateway (35s) < client (45s).

    Each layer outward must be strictly larger, or the outer one discards a
    good answer the inner one is still producing. These three numbers live
    in three different files, so nothing but a test keeps them in order.
    """
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "services" / "gateway"))
    from gateway.router import HTTP_TIMEOUT as gateway_timeout

    client_timeout = 45  # client/api_client.py send_chat

    assert TOTAL_BUDGET_SECONDS < gateway_timeout, "gateway would discard a good AI answer"
    assert gateway_timeout < client_timeout, "client would give up before the gateway"


def test_a_slow_model_does_not_consume_the_whole_budget_twice(monkeypatch):
    """Each attempt is capped by what is LEFT, not by the full per-request
    timeout, so the sequence cannot overrun."""
    seen_timeouts = []

    def slow_request(**kwargs):
        seen_timeouts.append(kwargs["timeout"])
        # Pretend each attempt burns most of the budget, then fails.
        monkeypatch.setattr(completion.time, "monotonic", _advance(12.0))
        return AIResponse(error="timed out")

    def _advance(seconds):
        base = completion.time.monotonic()
        return lambda: base + seconds

    monkeypatch.setattr(completion, "_request_ollama_native", slow_request)
    monkeypatch.setattr(completion, "_request_openai_streaming", slow_request)

    get_ai_response("hello", health=healthy())

    assert seen_timeouts, "no attempt was made"
    assert all(t <= TOTAL_BUDGET_SECONDS for t in seen_timeouts)


def test_the_budget_stops_the_retry_sequence(monkeypatch):
    """Once the budget is spent, remaining models/attempts are abandoned
    rather than run to completion for a caller who already gave up."""
    calls = {"n": 0}
    start = time.monotonic()

    def failing_request(**kwargs):
        calls["n"] += 1
        return AIResponse(error="boom")

    # Freeze "now" past the deadline after the first attempt.
    times = iter([start, start, start + TOTAL_BUDGET_SECONDS + 1])

    def fake_monotonic():
        try:
            return next(times)
        except StopIteration:
            return start + TOTAL_BUDGET_SECONDS + 1

    monkeypatch.setattr(completion, "_request_ollama_native", failing_request)
    monkeypatch.setattr(completion, "_request_openai_streaming", failing_request)
    monkeypatch.setattr(completion.time, "monotonic", fake_monotonic)

    result = get_ai_response("hello", health=healthy())

    assert calls["n"] < 4, "the full 4-attempt sequence ran despite the budget"
    assert result.error


def test_budget_exhaustion_is_logged_at_error(monkeypatch, caplog):
    import logging

    start = time.monotonic()
    monkeypatch.setattr(
        completion, "_request_ollama_native", lambda **kw: AIResponse(error="boom")
    )
    monkeypatch.setattr(
        completion, "_request_openai_streaming", lambda **kw: AIResponse(error="boom")
    )
    times = iter([start, start, start + TOTAL_BUDGET_SECONDS + 1])
    monkeypatch.setattr(
        completion.time, "monotonic",
        lambda: next(times, start + TOTAL_BUDGET_SECONDS + 1),
    )

    with caplog.at_level(logging.ERROR, logger=completion.__name__):
        get_ai_response("hello", health=healthy())

    assert "AI_BUDGET_EXHAUSTED" in caplog.text


def test_a_fast_success_is_unaffected(monkeypatch):
    """The budget must not change the normal path in any way."""
    ok = lambda **kw: AIResponse(
        spoken_text="Docker is a container platform.",
        full_text="Docker is a container platform.",
        model_used="jarvis",
    )
    # Which transport is used depends on the configured base_url, so patch
    # both -- host.docker.internal routes to the OpenAI-compatible client.
    monkeypatch.setattr(completion, "_request_ollama_native", ok)
    monkeypatch.setattr(completion, "_request_openai_streaming", ok)

    result = get_ai_response("what is docker", health=healthy())

    assert result.spoken_text == "Docker is a container platform."
    assert result.error == ""
