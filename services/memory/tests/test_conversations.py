"""Conversation persistence.

The endpoints existed since the migration but had no caller, so the Neon
`conversations` table stayed empty while every turn was answered and thrown
away. These pin the contract the gateway now writes against.
"""


async def test_a_turn_is_stored_and_read_back(client):
    posted = await client.post(
        "/conversations",
        json={"role": "user", "content": "what is a transformer",
              "source": "ai", "session_id": "abc123"},
    )
    assert posted.status_code == 201

    listed = await client.get("/conversations")
    body = listed.json()

    assert len(body) == 1
    assert body[0]["role"] == "user"
    assert body[0]["content"] == "what is a transformer"
    assert body[0]["source"] == "ai"
    assert body[0]["session_id"] == "abc123"


async def test_conversations_read_back_in_chronological_order(client):
    """A transcript is useless if the answer precedes the question."""
    for role, content in [("user", "first"), ("assistant", "second"), ("user", "third")]:
        await client.post(
            "/conversations",
            json={"role": role, "content": content, "source": "ai", "session_id": "s1"},
        )

    body = (await client.get("/conversations")).json()
    assert [row["content"] for row in body] == ["first", "second", "third"]


async def test_conversations_can_be_filtered_by_session(client):
    await client.post("/conversations", json={"role": "user", "content": "in session one", "session_id": "s1"})
    await client.post("/conversations", json={"role": "user", "content": "in session two", "session_id": "s2"})

    body = (await client.get("/conversations", params={"session_id": "s1"})).json()

    assert [row["content"] for row in body] == ["in session one"]


async def test_source_and_session_are_optional(client):
    """Rows written before these columns existed have neither."""
    posted = await client.post("/conversations", json={"role": "user", "content": "bare row"})

    assert posted.status_code == 201
    assert posted.json()["source"] is None
    assert posted.json()["session_id"] is None


async def test_an_invalid_role_is_rejected(client):
    response = await client.post("/conversations", json={"role": "robot", "content": "nope"})
    assert response.status_code == 422


async def test_the_limit_is_honoured(client):
    for index in range(5):
        await client.post("/conversations", json={"role": "user", "content": f"turn {index}"})

    body = (await client.get("/conversations", params={"limit": 2})).json()
    assert len(body) == 2
