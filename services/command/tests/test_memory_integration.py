"""command-service -> memory-service HTTP contract.

These assert the request shape command-service sends, which is the contract
that broke before (list-vs-dict on /memories, and the reminder field names).
"""


async def test_name_is_stored_as_a_memory(client, memory_service):
    response = await client.post("/execute", json={"text": "my name is Omair"})
    body = response.json()
    assert body["handled"] is True
    assert "Omair" in body["response"]
    assert ("POST", "/memories", {"key": "name", "value": "Omair"}) in memory_service.calls


async def test_remember_that_appends_to_notes_list(client, memory_service):
    await client.post("/execute", json={"text": "remember that I take coffee black"})
    await client.post("/execute", json={"text": "remember that my gym is on 5th street"})

    assert memory_service.memories["notes"] == [
        "I take coffee black",
        "my gym is on 5th street",
    ]


async def test_memory_summary_reads_list_shaped_response(client, memory_service):
    """memory-service returns a LIST of {key,value}; the handler must convert
    it. This was a real crash before _memory_list_to_dict existed."""
    memory_service.memories = {"name": "Omair", "notes": ["likes espresso"]}

    response = await client.post("/execute", json={"text": "what do you remember about me"})
    body = response.json()
    assert "Omair" in body["response"]
    assert "likes espresso" in body["response"]


async def test_memory_summary_when_nothing_stored(client):
    response = await client.post("/execute", json={"text": "what do you remember about me"})
    assert "not stored anything personal" in response.json()["response"]


async def test_memory_failure_degrades_gracefully(client, memory_service):
    memory_service.fail_next = True
    response = await client.post("/execute", json={"text": "what do you remember about me"})
    assert response.status_code == 200
    assert response.json()["handled"] is True


async def test_reminder_uses_scheduled_at_field(client, memory_service):
    """The command/memory reminder contract is {text, scheduled_at} — a
    previous mismatch here ('time' vs 'scheduled_at') broke reminders."""
    response = await client.post("/execute", json={"text": "remind me to call mom at 5 PM"})
    body = response.json()
    assert body["handled"] is True
    assert "call mom" in body["response"]

    posts = [call for call in memory_service.calls if call[0] == "POST" and call[1] == "/reminders"]
    assert len(posts) == 1
    payload = posts[0][2]
    assert payload["text"] == "call mom"
    assert "scheduled_at" in payload


async def test_unparseable_reminder_time_is_reported(client, memory_service):
    response = await client.post("/execute", json={"text": "remind me to call mom at sometime soon"})
    assert "more clearly" in response.json()["response"]
    assert not [c for c in memory_service.calls if c[1] == "/reminders" and c[0] == "POST"]


async def test_list_reminders_formats_scheduled_at(client, memory_service):
    memory_service.reminders = [
        {"id": 1, "text": "call mom", "scheduled_at": "2026-08-28T17:00:00", "triggered": False}
    ]
    response = await client.post("/execute", json={"text": "show my reminders"})
    body = response.json()
    assert "call mom" in body["response"]
    assert "5:00 PM" in body["response"]


async def test_list_reminders_when_empty(client):
    response = await client.post("/execute", json={"text": "show my reminders"})
    assert "do not have any active reminders" in response.json()["response"]
