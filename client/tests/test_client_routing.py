"""Client routing: the wake state machine, and voice/text dispatch parity.

These stub the microphone and the gateway, so they cover the parts of the
voice path that a human mic test cannot check repeatably -- in particular
that widening the wake rule did not make an awake JARVIS swallow every
command that happens to say its own name.
"""

from types import SimpleNamespace

import pytest

import desktop_app
from desktop_app import JarvisClient


class FakeVoiceEngine:
    """Stands in for VoiceEngine so no model, mic or speaker is touched."""

    def __init__(self, *args, **kwargs) -> None:
        self.spoken: list[str] = []
        self.listening = False

    def speak_async(self, text: str) -> None:
        self.spoken.append(text)

    def listen_continuously(self, **kwargs) -> None:
        self.listening = True

    def stop(self) -> None:
        self.listening = False


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(desktop_app, "VoiceEngine", FakeVoiceEngine)

    sent: list[str] = []

    def fake_send_chat(text, **kwargs):
        sent.append(text)
        return SimpleNamespace(
            error=None,
            source="command",
            spoken_text="ok",
            full_text="ok",
            action=None,
            action_target=None,
            action_data=None,
        )

    monkeypatch.setattr(desktop_app, "send_chat", fake_send_chat)

    instance = JarvisClient({"owner_name": "Omair", "workspace_dir": str(tmp_path)})
    instance.sent = sent
    return instance


def test_speech_is_ignored_while_asleep(client):
    client.on_recognized_text("what time is it")
    assert client.active is False
    assert client.sent == []


def test_wake_word_activates_and_greets(client):
    client.on_recognized_text("jarvis")
    assert client.active is True
    assert any("online" in line.lower() for line in client.voice_engine.spoken)


def test_a_misheard_wake_word_still_activates(client):
    """"journal" was a real session 1 transcription of "jarvis"."""
    client.on_recognized_text("journal")
    assert client.active is True


def test_an_awake_jarvis_does_not_swallow_commands_naming_itself(client):
    """Regression guard for the wake widening: matching the wake word
    anywhere at all times would turn every "jarvis, ..." command into
    another wake greeting instead of an answer."""
    client.on_recognized_text("jarvis")
    client.voice_engine.spoken.clear()

    client._handle_text("jarvis what time is it")

    assert client.sent == ["jarvis what time is it"]


def test_the_exit_phrase_deactivates(client):
    client.on_recognized_text("jarvis")
    client.on_recognized_text("thank you jarvis")

    assert client.active is False
    assert client.sent == []


def test_corrections_are_applied_before_the_gateway_sees_the_text(client):
    client.on_recognized_text("jarvis")
    client._handle_text(desktop_app.apply_stt_corrections("call me omar"))

    assert client.sent == ["call me Omair"]


# ── Text mode ───────────────────────────────────────────────────────────


def test_text_mode_needs_no_wake_word(client):
    client.start_text_mode()
    assert client.active is True


def test_typed_text_uses_the_same_gateway_call(client):
    client.start_text_mode()
    client.handle_typed_text("what time is it in Paris")

    assert client.sent == ["what time is it in Paris"]


def test_typed_text_dispatches_local_actions(client, monkeypatch):
    dispatched: list[tuple] = []
    monkeypatch.setattr(
        desktop_app.JarvisClient,
        "_dispatch_action",
        lambda self, a, t, d: dispatched.append((a, t, d)),
    )
    monkeypatch.setattr(
        desktop_app,
        "send_chat",
        lambda text, **kw: SimpleNamespace(
            error=None,
            source="command",
            spoken_text="Opening Google Chrome.",
            full_text="",
            action="launch",
            action_target="chrome",
            action_data=None,
        ),
    )

    client.start_text_mode()
    client.handle_typed_text("open chrome")

    assert dispatched == [("launch", "chrome", None)]


def test_typed_text_is_not_run_through_the_stt_corrections(client):
    """Typed input has no misrecognitions to repair; correcting it would
    rewrite a deliberately typed name."""
    client.start_text_mode()
    client.handle_typed_text("remember that john is my manager")

    assert client.sent == ["remember that john is my manager"]


def test_typed_text_updates_chat_history_like_voice(client):
    client.start_text_mode()
    client.handle_typed_text("hello")

    assert client.chat_history == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "ok"},
    ]
