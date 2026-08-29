"""Routing contract: which utterances command-service handles vs. defers to AI."""
import pytest


async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "command-service"


async def test_empty_input_is_handled_not_forwarded(client):
    response = await client.post("/execute", json={"text": "   "})
    body = response.json()
    assert body["handled"] is True
    assert body["action"] != "ai_fallback"


@pytest.mark.parametrize(
    "text",
    [
        "what is the meaning of quantum entanglement",
        "write me a poem about the sea",
        "why is the sky blue",
    ],
)
async def test_open_ended_questions_defer_to_ai(client, text):
    """The gateway only falls through to ai-service when handled is False
    and action is ai_fallback — see gateway/router.py."""
    response = await client.post("/execute", json={"text": text})
    body = response.json()
    assert body["handled"] is False
    assert body["action"] == "ai_fallback"


@pytest.mark.parametrize(
    "text",
    ["what time is it", "what's the time", "time", "tell me the current time"],
)
async def test_time_queries_are_handled_locally(client, text):
    response = await client.post("/execute", json={"text": text})
    body = response.json()
    assert body["handled"] is True
    assert body["response"].startswith("The time is")


@pytest.mark.parametrize("text", ["what is today's date", "what day is it"])
async def test_date_queries_are_handled_locally(client, text):
    response = await client.post("/execute", json={"text": text})
    body = response.json()
    assert body["handled"] is True
    assert body["response"].startswith("Today's date is")


async def test_time_for_is_not_treated_as_a_time_query(client):
    """"time for" is explicitly excluded so "time for a break" reaches the AI."""
    response = await client.post("/execute", json={"text": "is it time for a break"})
    body = response.json()
    assert not body["response"].startswith("The time is")


async def test_time_in_another_country_should_not_return_local_time(client):
    """Was a known bug (answered with the local clock, ignoring the location).
    Fixed by command_service/timeloc.py — see tests/test_timeloc.py."""
    response = await client.post("/execute", json={"text": "what time is it in japan"})
    body = response.json()
    assert body["handled"] is False or "japan" in body["response"].lower()
    # The local-clock phrasing would mean the location was dropped again.
    assert not body["response"].startswith("The time is ")
