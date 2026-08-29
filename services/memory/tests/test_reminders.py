from datetime import datetime, timedelta, timezone


async def test_reminder_create_and_list(client):
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    response = await client.post("/reminders", json={"text": "call mom", "scheduled_at": future})
    assert response.status_code == 201
    body = response.json()
    assert body["text"] == "call mom"
    assert body["triggered"] is False

    response = await client.get("/reminders")
    assert response.status_code == 200
    assert any(r["text"] == "call mom" for r in response.json())


async def test_check_reminders_triggers_due_reminder(client):
    past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    create_response = await client.post("/reminders", json={"text": "due now", "scheduled_at": past})
    assert create_response.status_code == 201

    # Not yet triggered, so it still shows in the default (non-triggered) list.
    listed = await client.get("/reminders")
    assert any(r["text"] == "due now" for r in listed.json())

    check_response = await client.post("/reminders/check")
    assert check_response.status_code == 200
    triggered = check_response.json()["triggered"]
    assert any(r["text"] == "due now" for r in triggered)

    # Once triggered, it drops out of the default (non-triggered) list...
    listed_after = await client.get("/reminders")
    assert not any(r["text"] == "due now" for r in listed_after.json())

    # ...but is still visible with include_triggered=True.
    listed_all = await client.get("/reminders", params={"include_triggered": True})
    assert any(r["text"] == "due now" for r in listed_all.json())

    # A second check should not re-trigger it.
    second_check = await client.post("/reminders/check")
    assert not any(r["text"] == "due now" for r in second_check.json()["triggered"])


async def test_check_reminders_ignores_future_reminders(client):
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    await client.post("/reminders", json={"text": "not yet", "scheduled_at": future})

    check_response = await client.post("/reminders/check")
    assert not any(r["text"] == "not yet" for r in check_response.json()["triggered"])
