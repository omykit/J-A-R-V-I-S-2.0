"""Time requests through the real /execute endpoint.

Complements test_timeloc.py's unit tests: these confirm the handler branch
is actually wired up and that time requests stay handled=True (so the
gateway answers with source "command" rather than falling through to the LLM).
"""
import pytest

# Geolocation is stubbed to Asia/Kuwait for every test by an autouse
# fixture in conftest.py, so these never touch the network.


async def execute(client, text: str) -> dict:
    response = await client.post("/execute", json={"text": text})
    assert response.status_code == 200
    return response.json()


async def test_explicit_location_is_handled_by_command_service(client):
    body = await execute(client, "What time is it in Tokyo?")
    assert body["handled"] is True
    assert "Tokyo" in body["response"]


async def test_explicit_location_not_answered_with_default_zone(client):
    tokyo = await execute(client, "What time is it in Tokyo?")
    local = await execute(client, "What time is it?")
    # The original bug: both returned the same (wrong) clock time.
    assert tokyo["response"] != local["response"]


@pytest.mark.parametrize(
    "text",
    [
        "What time is it?",
        "What is the current time?",
        "Tell me the time.",
        "Give me the time.",
        "Can you check the time?",
        "Tell me the time in London.",
        "Give me the time in New York.",
    ],
)
async def test_time_requests_stay_in_command_service(client, text):
    body = await execute(client, text)
    assert body["handled"] is True
    assert body["action"] != "ai_fallback"


async def test_unknown_location_handled_without_inventing_a_time(client):
    body = await execute(client, "What time is it in Wakanda?")
    # Still handled (so it doesn't reach the LLM) but reports no clock time.
    assert body["handled"] is True
    assert "Wakanda" in body["response"]
    assert "AM" not in body["response"] and "PM" not in body["response"]


async def test_non_time_request_still_falls_through_to_ai(client):
    body = await execute(client, "explain quantum entanglement to me")
    assert body["handled"] is False
    assert body["action"] == "ai_fallback"
