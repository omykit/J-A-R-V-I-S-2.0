"""Startup preflight.

Session 2 spent four minutes producing apologies because Ollama was not
running. The Ollama server log shows no listener until 15:48:04 while the
outage window was 15:43-15:47, and connection-refused fails in ~5ms -- so
every turn was answered from the fallback string without Ollama ever being
called. The outage was not the defect. The silence was.
"""

from desktop_app import preflight


def ok_health(**overrides):
    ai = {"status": "ok", "detail": "Ollama is available",
          "models": ["jarvis", "llama3"], "model": "jarvis"}
    ai.update(overrides.pop("ai", {}))
    return {"status": "ok", "services": {"memory": {"status": "ok"},
                                         "command": {"status": "ok"}, "ai": ai}}


def test_a_healthy_stack_starts():
    assert preflight(ok_health()) == ""


def test_an_unreachable_gateway_is_reported():
    message = preflight({"status": "unreachable", "services": {}})
    assert "gateway is not reachable" in message
    assert "docker compose up -d" in message


def test_ollama_down_is_named_explicitly():
    """The exact case that happened: Ollama not running."""
    message = preflight(ok_health(ai={"status": "unavailable",
                                      "detail": "<urlopen error [Errno 111] Connection refused>"}))

    assert "Ollama is not reachable" in message
    assert "Start Ollama, then run this again." in message
    # The underlying reason must survive to the user, not be swallowed.
    assert "Connection refused" in message


def test_a_degraded_ai_service_also_blocks_startup():
    message = preflight(ok_health(ai={"status": "degraded", "detail": "No Ollama models installed"}))
    assert "Ollama is not reachable" in message
    assert "No Ollama models installed" in message


def test_a_missing_configured_model_blocks_startup():
    """Reachable is not enough. If the model is absent, every turn would
    fail at request time instead of once, clearly, at startup."""
    message = preflight(ok_health(ai={"status": "ok", "models": ["llama3"], "model": "jarvis"}))

    assert "model 'jarvis' is missing" in message
    assert "llama3" in message
    assert "ollama pull jarvis" in message


def test_the_configured_model_being_present_passes():
    assert preflight(ok_health(ai={"status": "ok", "models": ["jarvis", "qwen3"], "model": "jarvis"})) == ""


def test_an_unknown_model_list_does_not_block():
    """An older ai-service reports no model/models; do not fail closed on it."""
    assert preflight(ok_health(ai={"status": "ok", "models": [], "model": ""})) == ""


def test_a_degraded_memory_service_does_not_block_startup():
    """Conversation logging is best-effort; it must not gate startup."""
    health = ok_health()
    health["services"]["memory"] = {"status": "unreachable"}
    health["status"] = "degraded"

    assert preflight(health) == ""
