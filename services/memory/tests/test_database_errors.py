"""A database blip must read as 503, not as a 500 with a traceback.

Observed on 2026-08-31 at 18:03 UTC: Neon's hostname failed to resolve
inside the container and socket.gaierror escaped as an unhandled ASGI
exception, so POST /reminders/check returned 500 with a full stack trace.
The gateway polls that endpoint every 30 seconds, which makes it the most
exposed endpoint in the service.

503 is the honest status: temporary and retryable, so a caller can back off,
rather than a 500 that reads like a bug in the request.
"""

import pytest
from sqlalchemy.exc import OperationalError

from memory_service import repository as repo


@pytest.fixture
def broken_db(monkeypatch):
    """Make every repository call fail the way a DNS blip does."""
    def gaierror(*args, **kwargs):
        raise OSError(-2, "Name or service not known")

    for name in ("get_all_memories", "check_reminders", "list_reminders",
                 "get_recent_conversations"):
        monkeypatch.setattr(repo, name, gaierror)


async def test_reminders_check_returns_503_not_500(client, broken_db):
    """The endpoint the gateway polls twice a minute."""
    response = await client.post("/reminders/check")

    assert response.status_code == 503
    assert "unreachable" in response.json()["detail"].lower()


async def test_the_traceback_is_not_leaked_to_the_caller(client, broken_db):
    response = await client.post("/reminders/check")
    body = response.text

    assert "Traceback" not in body
    assert "asyncpg" not in body
    assert "site-packages" not in body


async def test_listing_memories_degrades_to_503(client, broken_db):
    response = await client.get("/memories")
    assert response.status_code == 503


async def test_listing_conversations_degrades_to_503(client, broken_db):
    response = await client.get("/conversations")
    assert response.status_code == 503


async def test_a_sqlalchemy_error_also_becomes_503(client, monkeypatch):
    """Not every failure is a socket error -- a dropped pool connection
    surfaces as SQLAlchemy's own exception type."""
    def boom(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("connection lost"))

    monkeypatch.setattr(repo, "get_all_memories", boom)

    response = await client.get("/memories")

    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"].lower()


async def test_the_error_type_is_reported_for_diagnosis(client, broken_db):
    """Empty error messages are what made the gateway's "Reminder check
    failed: " line undebuggable. Always carry the exception type."""
    response = await client.post("/reminders/check")
    assert response.json()["error"] == "OSError"


async def test_healthy_requests_are_completely_unaffected(client):
    """The handlers change the failure shape only."""
    assert (await client.get("/memories")).status_code == 200
    assert (await client.post("/reminders/check")).status_code == 200
    assert (await client.get("/conversations")).status_code == 200

    created = await client.post("/memories", json={"key": "k", "value": "v"})
    assert created.status_code == 201


async def test_a_missing_key_is_still_404_not_503(client):
    """A genuine client error must not be masked as a service outage."""
    response = await client.get("/memories/does-not-exist")
    assert response.status_code == 404
