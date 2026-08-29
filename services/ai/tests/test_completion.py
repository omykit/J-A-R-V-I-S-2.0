from ai_service.completion import build_memory_context, fallback_ai_response, prepare_messages


def test_fallback_ai_response_spoken_matches_full_text():
    # Regression test: fallback_ai_response() used to call the random choice
    # twice independently, so spoken_text and full_text could mismatch.
    for _ in range(20):
        response = fallback_ai_response(error="boom")
        assert response.spoken_text == response.full_text
        assert response.error == "boom"


def test_build_memory_context_empty():
    assert build_memory_context([]) == ""


def test_build_memory_context_formats_known_facts():
    context = build_memory_context([{"key": "name", "value": "Omair"}])
    assert "name: Omair" in context


def test_prepare_messages_includes_owner_name_and_history():
    messages = prepare_messages(
        "hello",
        system_prompt="Assist the user.",
        chat_history=[{"role": "user", "content": "hi"}],
        memory_context="",
        owner_name="Omair",
        max_history=5,
    )
    assert messages[0]["role"] == "system"
    assert "Omair" in messages[0]["content"]
    assert messages[-1] == {"role": "user", "content": "hello"}
