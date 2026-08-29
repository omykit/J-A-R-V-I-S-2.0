"""Gateway routing: command-service first, ai-service on fallback.

This is the contract the whole system hangs on — the client only ever talks
to the gateway, so these tests pin the command-hit / command-miss behaviour
and the degradation path when a downstream service is unreachable.
"""
import httpx
import respx

from gateway.config import settings

COMMAND_URL = f"{settings.command_service_url}/execute"
AI_URL = f"{settings.ai_service_url}/chat"


@respx.mock
async def test_command_hit_is_returned_without_calling_ai(client):
    command_route = respx.post(COMMAND_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "handled": True,
                "response": "Opening Notepad.",
                "action": "launch",
                "action_target": "notepad",
                "focus_text": "Focused action: Notepad",
            },
        )
    )
    ai_route = respx.post(AI_URL).mock(return_value=httpx.Response(200, json={}))

    response = await client.post("/chat", json={"text": "open notepad"})
    body = response.json()

    assert response.status_code == 200
    assert body["source"] == "command"
    assert body["spoken_text"] == "Opening Notepad."
    assert body["action"] == "launch"
    assert body["action_target"] == "notepad"
    assert command_route.called
    assert not ai_route.called, "AI must not be called when the command service handles it"


@respx.mock
async def test_unhandled_command_falls_through_to_ai(client):
    respx.post(COMMAND_URL).mock(
        return_value=httpx.Response(200, json={"handled": False, "response": "", "action": "ai_fallback"})
    )
    ai_route = respx.post(AI_URL).mock(
        return_value=httpx.Response(
            200,
            json={"spoken_text": "The sky scatters blue light.", "full_text": "Long answer.", "model_used": "jarvis"},
        )
    )

    response = await client.post("/chat", json={"text": "why is the sky blue"})
    body = response.json()

    assert body["source"] == "ai"
    assert body["spoken_text"] == "The sky scatters blue light."
    assert body["full_text"] == "Long answer."
    assert body["model_used"] == "jarvis"
    assert ai_route.called


@respx.mock
async def test_ai_fallback_action_is_never_returned_as_a_command(client):
    """handled=True with action=ai_fallback must still route to the AI —
    the guard is `handled and action != "ai_fallback"` in router.py."""
    respx.post(COMMAND_URL).mock(
        return_value=httpx.Response(200, json={"handled": True, "response": "", "action": "ai_fallback"})
    )
    ai_route = respx.post(AI_URL).mock(
        return_value=httpx.Response(200, json={"spoken_text": "AI answer", "full_text": "AI answer"})
    )

    body = (await client.post("/chat", json={"text": "anything"})).json()
    assert body["source"] == "ai"
    assert ai_route.called


@respx.mock
async def test_command_service_down_still_reaches_ai(client):
    respx.post(COMMAND_URL).mock(side_effect=httpx.ConnectError("refused"))
    ai_route = respx.post(AI_URL).mock(
        return_value=httpx.Response(200, json={"spoken_text": "still here", "full_text": "still here"})
    )

    body = (await client.post("/chat", json={"text": "hello"})).json()
    assert body["source"] == "ai"
    assert ai_route.called


@respx.mock
async def test_both_services_down_returns_graceful_fallback(client):
    respx.post(COMMAND_URL).mock(side_effect=httpx.ConnectError("refused"))
    respx.post(AI_URL).mock(side_effect=httpx.ConnectError("refused"))

    response = await client.post("/chat", json={"text": "hello"})
    body = response.json()

    assert response.status_code == 200, "the client must get a speakable reply, not a 5xx"
    assert body["source"] == "fallback"
    assert body["spoken_text"]


@respx.mock
async def test_chat_history_and_owner_name_are_forwarded_to_ai(client):
    respx.post(COMMAND_URL).mock(
        return_value=httpx.Response(200, json={"handled": False, "response": "", "action": "ai_fallback"})
    )
    ai_route = respx.post(AI_URL).mock(
        return_value=httpx.Response(200, json={"spoken_text": "ok", "full_text": "ok"})
    )

    history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    await client.post(
        "/chat",
        json={"text": "and then?", "chat_history": history, "owner_name": "Omair"},
    )

    import json

    sent = json.loads(ai_route.calls.last.request.content)
    assert sent["chat_history"] == history
    assert sent["owner_name"] == "Omair"


@respx.mock
async def test_selected_and_last_action_are_forwarded_to_command(client):
    command_route = respx.post(COMMAND_URL).mock(
        return_value=httpx.Response(200, json={"handled": True, "response": "Opening.", "action": "launch"})
    )

    await client.post(
        "/chat",
        json={"text": "open this", "selected_action": "calculator", "last_action": "youtube"},
    )

    import json

    sent = json.loads(command_route.calls.last.request.content)
    assert sent["selected_action"] == "calculator"
    assert sent["last_action"] == "youtube"
