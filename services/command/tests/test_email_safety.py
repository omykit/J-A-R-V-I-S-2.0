"""Guards the email safety patch.

Jarvis has no email-sending capability. The safety property is that any
email-shaped request is intercepted deterministically and answered with an
honest refusal *before* it can reach the AI, so the model can never claim an
email was sent. These tests exist to catch a regression that would let an
email request slip through to ai_fallback.
"""
import pytest

from command_service.intents import EMAIL_UNCONFIGURED_RESPONSE


@pytest.mark.parametrize(
    "text",
    [
        "send me an email",
        "email me the summary",
        "can you email me the notes",
        "send this to my email",
        "set an email reminder for 5 pm",
        "configure email notifications",
        "send an email to omair@example.com",
        "notify omair@example.com about the meeting",
    ],
)
async def test_email_requests_are_refused_not_forwarded_to_ai(client, text):
    response = await client.post("/execute", json={"text": text})
    body = response.json()
    assert body["handled"] is True
    assert body["action"] != "ai_fallback"
    assert body["response"] == EMAIL_UNCONFIGURED_RESPONSE


async def test_email_refusal_precedes_every_other_branch(client):
    """The email check is the first branch in handle(), so an utterance that
    would otherwise match another intent still gets refused."""
    response = await client.post("/execute", json={"text": "what time is it, and email me the answer"})
    body = response.json()
    assert body["response"] == EMAIL_UNCONFIGURED_RESPONSE


async def test_non_email_requests_are_unaffected(client):
    response = await client.post("/execute", json={"text": "open notepad"})
    assert response.json()["response"] != EMAIL_UNCONFIGURED_RESPONSE
