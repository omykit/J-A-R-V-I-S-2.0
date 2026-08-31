"""The gateway is the missing caller of memory-service POST /conversations.

Nothing anywhere wrote conversation turns, which is the whole reason the
Neon table was empty. These cover what gets written, what does not, and --
most importantly -- that a logging failure can never break a live turn.
"""

import httpx
import pytest

from gateway import conversations


@pytest.fixture
def memory_writes(monkeypatch):
    """Capture what would be POSTed to memory-service."""
    writes: list[dict] = []

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, json=None, **kwargs):
            writes.append(json)
            return httpx.Response(201, json={"id": len(writes)})

    monkeypatch.setattr(conversations.httpx, "AsyncClient", FakeAsyncClient)
    return writes


AI_RESULT = {"source": "ai", "spoken_text": "A transformer is a model.", "full_text": "A transformer is a model."}


async def test_an_ai_turn_writes_a_user_and_an_assistant_row(memory_writes):
    written = await conversations.log_turn(
        user_text="what is a transformer", result=AI_RESULT, session_id="s1"
    )

    assert written is True
    assert [w["role"] for w in memory_writes] == ["user", "assistant"]
    assert memory_writes[0]["content"] == "what is a transformer"
    assert memory_writes[1]["content"] == "A transformer is a model."


async def test_the_session_id_and_source_are_recorded(memory_writes):
    await conversations.log_turn(user_text="hello", result=AI_RESULT, session_id="s1")

    assert all(w["session_id"] == "s1" for w in memory_writes)
    assert all(w["source"] == "ai" for w in memory_writes)


async def test_the_user_row_is_written_before_the_assistant_row(memory_writes):
    """created_at orders a transcript, so the two writes are sequential --
    concurrent inserts can share a timestamp and read back reversed."""
    await conversations.log_turn(user_text="q", result=AI_RESULT)

    assert memory_writes[0]["role"] == "user"
    assert memory_writes[1]["role"] == "assistant"


@pytest.mark.parametrize("source", ["command", "fallback", ""])
async def test_non_ai_turns_are_not_logged(source, memory_writes):
    """Scope is AI turns only; deterministic command turns are high volume
    and low value. Widening is a one-line change to LOGGED_SOURCES."""
    written = await conversations.log_turn(
        user_text="what time is it",
        result={"source": source, "spoken_text": "The time is 4:00 PM."},
    )

    assert written is False
    assert memory_writes == []


async def test_an_empty_turn_is_not_logged(memory_writes):
    written = await conversations.log_turn(
        user_text="   ", result={"source": "ai", "spoken_text": "", "full_text": ""}
    )

    assert written is False
    assert memory_writes == []


async def test_a_memory_service_outage_never_breaks_the_turn(monkeypatch):
    """The single most important property here. If Neon or memory-service is
    down, the user must still get their answer -- they just lose the
    transcript for that turn."""

    class ExplodingClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, *args, **kwargs):
            raise httpx.ConnectError("memory-service is down")

    monkeypatch.setattr(conversations.httpx, "AsyncClient", ExplodingClient)

    written = await conversations.log_turn(user_text="hello", result=AI_RESULT)

    assert written is False  # reported, not raised


async def test_a_rejected_write_is_warned_not_raised(monkeypatch, caplog):
    class RejectingClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, *args, **kwargs):
            return httpx.Response(422, json={"detail": "bad"})

    monkeypatch.setattr(conversations.httpx, "AsyncClient", RejectingClient)

    with caplog.at_level("WARNING"):
        await conversations.log_turn(user_text="hello", result=AI_RESULT)

    assert "conversation_log_rejected" in caplog.text


async def test_chat_endpoint_logs_without_blocking_the_response(client, memory_writes, monkeypatch):
    """End to end through /chat: the reply is returned, and the turn is
    logged on a background task rather than in the request path."""
    async def fake_route_text(text, **kwargs):
        return dict(AI_RESULT)

    from gateway import main as gateway_main

    monkeypatch.setattr(gateway_main, "route_text", fake_route_text)

    response = await client.post(
        "/chat", json={"text": "what is a transformer", "session_id": "s9"}
    )

    assert response.status_code == 200
    assert response.json()["spoken_text"] == "A transformer is a model."

    # The write is queued, not awaited, so let the worker drain it.
    await conversations.wait_until_drained()

    assert [w["role"] for w in memory_writes] == ["user", "assistant"]
    assert all(w["session_id"] == "s9" for w in memory_writes)


async def test_consecutive_turns_are_not_interleaved(memory_writes):
    """Regression test for a defect caught on the first live run.

    Dispatching one background task per turn stored two back-to-back
    questions as user(Q1), user(Q2), assistant(A1), assistant(A2) -- the
    transcript read every question first, then every answer. Writes are now
    serialised through a single worker in submission order.
    """
    for index in (1, 2, 3):
        conversations.log_turn_in_background(
            user_text=f"question {index}",
            result={"source": "ai", "spoken_text": f"answer {index}", "full_text": f"answer {index}"},
            session_id="s1",
        )

    await conversations.wait_until_drained()

    assert [w["content"] for w in memory_writes] == [
        "question 1", "answer 1",
        "question 2", "answer 2",
        "question 3", "answer 3",
    ]
