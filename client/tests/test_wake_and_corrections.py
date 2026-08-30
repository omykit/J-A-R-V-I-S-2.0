"""Wake matching and the post-STT correction map.

Session 1 took 1 minute 37 seconds and six attempts to wake JARVIS. Two of
those failures were not speech-recognition errors at all: Vosk returned
"jarvis" at 0.88 confidence and "hello jarvis" at 0.81, cleanly, and the
matcher rejected both because it compared against five exact phrases.
"""

import pytest

from desktop_app import (
    WAKE_WORD,
    apply_stt_corrections,
    is_wake_utterance,
    normalize_utterance,
)


# ── 3a: wake matching ───────────────────────────────────────────────────

WAKES = [
    "jarvis",                       # Vosk 0.88, previously rejected
    "hello jarvis",                 # Vosk 0.81, previously rejected
    "hey jarvis",
    "hi jarvis",
    "are you up jarvis",
    "jarvis are you up",
    "hey jarvis are you up",
    "jarvis are you there",
    "ok jarvis",
    "Jarvis!",                      # casing and punctuation
]


@pytest.mark.parametrize("utterance", WAKES)
def test_wake_utterances_trigger(utterance):
    assert is_wake_utterance(utterance) is True


def test_the_two_rejected_session_1_utterances():
    """Both were transcribed correctly and still failed to wake."""
    assert is_wake_utterance("jarvis") is True
    assert is_wake_utterance("hello jarvis") is True


@pytest.mark.parametrize(
    "utterance",
    [
        "",
        "   ",
        "what time is it in Tokyo",
        "remember that I prefer Python",
        "open chrome",
    ],
)
def test_unrelated_speech_does_not_wake(utterance):
    assert is_wake_utterance(utterance) is False


def test_wake_word_must_be_a_whole_token():
    """Substring matching would wake on unrelated vocabulary."""
    assert is_wake_utterance("jarvisian") is False
    assert is_wake_utterance("the jarvisware release") is False


def test_normalisation_strips_punctuation_and_case():
    assert normalize_utterance("  Hey, JARVIS!!  ") == "hey jarvis"
    assert normalize_utterance("...") == ""


# ── 3b: post-STT correction map ─────────────────────────────────────────

WAKE_MISHEARINGS_FROM_LOG = ["joe was", "journal", "journalists", "john", "jarvos", "dervis"]


@pytest.mark.parametrize("misheard", WAKE_MISHEARINGS_FROM_LOG)
def test_seeded_wake_mishearings_are_corrected_and_wake(misheard):
    corrected = apply_stt_corrections(misheard)
    assert WAKE_WORD in corrected.lower()
    assert is_wake_utterance(corrected) is True


@pytest.mark.parametrize("misheard", ["omar", "omer", "olmert", "almond"])
def test_seeded_name_mishearings_are_corrected(misheard):
    assert apply_stt_corrections(f"call me {misheard}") == "call me Omair"


def test_name_correction_applies_mid_sentence():
    assert apply_stt_corrections("my name is omer") == "my name is Omair"


def test_wake_mishearing_is_corrected_at_the_end_too():
    assert is_wake_utterance(apply_stt_corrections("are you up journal")) is True


def test_wake_mishearing_mid_sentence_does_not_corrupt_dictation():
    """The whole reason wake corrections are edge-anchored: "john" is a real
    word people dictate. Correcting it anywhere would rewrite a stored note
    into nonsense."""
    text = "remember that john is my manager"
    assert apply_stt_corrections(text) == text


@pytest.mark.parametrize(
    "text",
    [
        "what time is it in Paris",
        "open chrome",
        "remember that I prefer Python",
        "create a folder called invoices",
        "remind me to call mom at 5 PM",
    ],
)
def test_normal_speech_is_left_untouched(text):
    assert apply_stt_corrections(text) == text


def test_corrections_compose_with_wake_matching():
    """The exact live failure mode: a misheard wake word plus a misheard
    name in one utterance."""
    corrected = apply_stt_corrections("journal call me omar")
    assert corrected == "jarvis call me Omair"
    assert is_wake_utterance(corrected) is True
