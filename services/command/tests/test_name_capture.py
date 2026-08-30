"""Name capture through the command -> memory contract.

Session 1 (live voice) produced three real attempts to set a name that were
all lost: "call me omair", "from now on you should address me as ...", and
"no no call me omer". None matched the single literal pattern "my name is",
so they fell through to the AI service -- which has no memory write path --
and it answered that it does not store information about individual users.
That was architecturally true for the path taken, which is why prompting
could not have fixed it. These tests pin the widened phrasing set.
"""

import pytest

from command_service.handler import CommandHandler


def handler() -> CommandHandler:
    """The name rules are pure string work, so no memory client is needed."""
    return CommandHandler.__new__(CommandHandler)


PHRASINGS = [
    ("my name is Omair", "Omair"),
    ("call me omair", "Omair"),
    ("you can call me omair", "Omair"),
    ("my name's omair", "Omair"),
    ("address me as omair", "Omair"),
    ("from now on call me omair", "Omair"),
]


@pytest.mark.parametrize("utterance,expected", PHRASINGS)
async def test_every_phrasing_stores_the_name(utterance, expected, client, memory_service):
    response = await client.post("/execute", json={"text": utterance})
    body = response.json()

    assert body["handled"] is True
    assert expected in body["response"]
    assert ("POST", "/memories", {"key": "name", "value": expected}) in memory_service.calls


@pytest.mark.parametrize("utterance,expected", PHRASINGS)
def test_every_phrasing_extracts_the_name(utterance, expected):
    assert handler()._extract_spoken_name(utterance) == expected


def test_the_exact_session_1_utterances():
    """The three phrasings that were actually lost in live testing."""
    h = handler()
    assert h._extract_spoken_name("call me omair") == "Omair"
    assert h._extract_spoken_name("from now on you should address me as omair") == "Omair"
    assert h._extract_spoken_name("no no call me omer") == "Omer"


def test_trailing_stt_garble_is_cut_at_the_connector():
    """Vosk emitted "call me omer or m a r omer" -- storing the whole tail
    would make every later greeting read back the garble."""
    assert handler()._extract_spoken_name("call me omer or m a r omer") == "Omer"


def test_stray_single_letters_are_dropped():
    """Vosk spells letters out when it loses a word."""
    assert handler()._extract_spoken_name("call me omair k t r") == "Omair"


def test_a_first_and_last_name_are_both_kept():
    assert handler()._extract_spoken_name("my name is omair kittur") == "Omair Kittur"


def test_no_more_than_two_tokens_are_trusted():
    assert handler()._extract_spoken_name("call me omair kittur something else") == "Omair Kittur"


def test_existing_capitalisation_is_preserved():
    """Capitalise only what was heard in lower case."""
    assert handler()._extract_spoken_name("my name is McDonald") == "McDonald"


@pytest.mark.parametrize("utterance", ["call me back later", "call me a taxi", "call me an ambulance"])
def test_call_me_as_an_ordinary_request_is_not_a_name(utterance):
    """"call me" is not always a naming intent. These must fall through to
    normal routing rather than storing "Back" or "A" as the user's name."""
    assert handler()._extract_spoken_name(utterance) is None


async def test_a_non_name_call_me_is_not_written_to_memory(client, memory_service):
    await client.post("/execute", json={"text": "call me back later"})
    assert not [c for c in memory_service.calls if c[0] == "POST" and c[1] == "/memories"]


def test_unrelated_speech_has_no_name_intent():
    h = handler()
    assert h._extract_spoken_name("what time is it in Tokyo") is None
    assert h._extract_spoken_name("remember that I prefer Python") is None


async def test_reminder_phrasing_still_wins_over_name_capture(client, memory_service):
    """Reminders are matched before names; "remind me to call mom at 5 PM"
    must not be diverted into the name path."""
    response = await client.post("/execute", json={"text": "remind me to call mom at 5 PM"})

    assert "call mom" in response.json()["response"]
    assert not [c for c in memory_service.calls if c[0] == "POST" and c[1] == "/memories"]
