"""Gateway /health aggregation and the reminder-delivery bridge."""
import httpx
import respx

from gateway import reminders
from gateway.config import settings

AI_HEALTH = f"{settings.ai_service_url}/health"
COMMAND_HEALTH = f"{settings.command_service_url}/health"
MEMORY_HEALTH = f"{settings.memory_service_url}/health"
REMINDERS_CHECK = f"{settings.memory_service_url}/reminders/check"


def _all_healthy():
    for url in (AI_HEALTH, COMMAND_HEALTH, MEMORY_HEALTH):
        respx.get(url).mock(return_value=httpx.Response(200, json={"status": "ok"}))


@respx.mock
async def test_health_ok_when_all_services_healthy(client):
    _all_healthy()
    body = (await client.get("/health")).json()
    assert body["status"] == "ok"
    assert set(body["services"]) == {"memory", "ai", "command"}


@respx.mock
async def test_health_degraded_when_one_service_is_down(client):
    respx.get(MEMORY_HEALTH).mock(return_value=httpx.Response(200, json={"status": "ok"}))
    respx.get(COMMAND_HEALTH).mock(return_value=httpx.Response(200, json={"status": "ok"}))
    respx.get(AI_HEALTH).mock(side_effect=httpx.ConnectError("refused"))

    body = (await client.get("/health")).json()
    assert body["status"] == "degraded"
    assert body["services"]["ai"]["status"] == "unreachable"


@respx.mock
async def test_health_degraded_on_non_200(client):
    respx.get(MEMORY_HEALTH).mock(return_value=httpx.Response(503))
    respx.get(COMMAND_HEALTH).mock(return_value=httpx.Response(200, json={"status": "ok"}))
    respx.get(AI_HEALTH).mock(return_value=httpx.Response(200, json={"status": "ok"}))

    body = (await client.get("/health")).json()
    assert body["status"] == "degraded"
    assert body["services"]["memory"]["status"] == "error"


# ── Reminder bridge ──


def _drain():
    reminders.pop_pending()


@respx.mock
async def test_check_once_buffers_triggered_reminders(client):
    _drain()
    respx.post(REMINDERS_CHECK).mock(
        return_value=httpx.Response(200, json={"triggered": [{"id": 1, "text": "call mom"}]})
    )

    triggered = await reminders.check_once()
    assert [r["text"] for r in triggered] == ["call mom"]

    body = (await client.get("/reminders/pending")).json()
    assert [r["text"] for r in body["reminders"]] == ["call mom"]


@respx.mock
async def test_pending_reminders_are_drained_once(client):
    _drain()
    respx.post(REMINDERS_CHECK).mock(
        return_value=httpx.Response(200, json={"triggered": [{"id": 1, "text": "call mom"}]})
    )
    await reminders.check_once()

    first = (await client.get("/reminders/pending")).json()
    second = (await client.get("/reminders/pending")).json()

    assert len(first["reminders"]) == 1
    assert second["reminders"] == [], "a reminder must not be spoken twice"


@respx.mock
async def test_check_once_survives_memory_service_being_down(client):
    _drain()
    respx.post(REMINDERS_CHECK).mock(side_effect=httpx.ConnectError("refused"))

    assert await reminders.check_once() == []
    body = (await client.get("/reminders/pending")).json()
    assert body["reminders"] == []


@respx.mock
async def test_pending_is_empty_when_nothing_is_due(client):
    _drain()
    respx.post(REMINDERS_CHECK).mock(return_value=httpx.Response(200, json={"triggered": []}))

    await reminders.check_once()
    body = (await client.get("/reminders/pending")).json()
    assert body["reminders"] == []
