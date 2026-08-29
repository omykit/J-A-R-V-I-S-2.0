import time

import ai_service.main as main
from ai_service.ollama import OllamaHealth


async def test_chat_falls_back_when_ollama_unavailable(client, monkeypatch):
    # checked_at must be "now", not stale — otherwise _get_fresh_health()
    # would treat this as stale and overwrite it with a real (unmocked)
    # check_ollama_health() network call.
    monkeypatch.setattr(
        main,
        "_ollama_health",
        OllamaHealth(checked_at=time.perf_counter(), available=False, error="Ollama unavailable"),
    )

    async def fake_fetch_memories():
        return []

    monkeypatch.setattr(main, "_fetch_memories", fake_fetch_memories)

    response = await client.post("/chat", json={"text": "hello"})
    assert response.status_code == 200
    body = response.json()
    assert body["spoken_text"] == body["full_text"]
    assert body["error"]


def test_get_fresh_health_refreshes_stale_cache(monkeypatch):
    # Regression test: /chat used to trust _ollama_health forever, so a
    # snapshot taken before a model was created in Ollama (e.g. "jarvis")
    # would never notice that model becoming available.
    stale = OllamaHealth(checked_at=time.perf_counter() - 999, available=True, models={"llama3"})
    fresh = OllamaHealth(checked_at=time.perf_counter(), available=True, models={"llama3", "jarvis"})
    monkeypatch.setattr(main, "_ollama_health", stale)
    monkeypatch.setattr(main, "check_ollama_health", lambda *a, **k: fresh)

    result = main._get_fresh_health()

    assert result is fresh
    assert "jarvis" in result.models


def test_get_fresh_health_reuses_recent_cache(monkeypatch):
    recent = OllamaHealth(checked_at=time.perf_counter(), available=True, models={"llama3"})
    monkeypatch.setattr(main, "_ollama_health", recent)

    def fail_if_called(*a, **k):
        raise AssertionError("should not re-check Ollama when the cache is still fresh")

    monkeypatch.setattr(main, "check_ollama_health", fail_if_called)

    assert main._get_fresh_health() is recent


async def test_health_reports_ok_when_ollama_available(client, monkeypatch):
    def fake_check_ollama_health(base_url, timeout_seconds):
        return OllamaHealth(checked_at=0.0, available=True, models={"jarvis"})

    monkeypatch.setattr(main, "check_ollama_health", fake_check_ollama_health)

    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "jarvis" in body["models"]


async def test_health_reports_unavailable_when_ollama_down(client, monkeypatch):
    def fake_check_ollama_health(base_url, timeout_seconds):
        return OllamaHealth(checked_at=0.0, available=False, error="connection refused", degraded=False)

    monkeypatch.setattr(main, "check_ollama_health", fake_check_ollama_health)

    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
