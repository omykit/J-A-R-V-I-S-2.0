"""Guard against fabricated current time/date claims from the AI service.

Cases marked SESSION are verbatim from JHIT session 1 (2026-08-29).
"""
import pytest

from ai_service.truthfulness import REFUSAL, asserts_current_time_or_date, guard_response


@pytest.mark.parametrize(
    "text",
    [
        # SESSION 1 failures — the reason this guard exists.
        "The time in India is 00:35 AM (assuming UTC+5:30).",
        "Yes, I am confident it's currently 00:35 AM in India.",
        "The time in the United States is 11:35 PM.",
        "Today's date is Saturday, August 29, 2026.",
        # Hedged fabrication must not slip through.
        "It should be roughly 12:30 AM there.",
        "It's probably around midnight in India.",
        "It might be around 4 PM in Tokyo.",
        # UTC-offset claims are equally fabricated.
        "India is about two hours ahead of you.",
        "They're 9 hours ahead of Kuwait.",
        "Tokyo is six hours behind us.",
        "Their time is 9 hours from yours.",
        # Reformatted / reordered.
        "The current time in Tokyo: 19:36.",
        "Right now it's 3:36 in the afternoon in Chicago.",
        "The current time is 14:05.",
        "In India, the local time is 12:30 AM.",
        "The time there is 12:30 AM.",
        "Local time is 00:35.",
        "That would be 12:30 AM in India.",
        "India: 12:30 AM.",
        "You're looking at about 12:30 AM over there.",
        "India is currently at 12:30 AM.",
        "Over there the clock reads 19:36.",
        "It has just turned midnight in India.",
        "12:30 AM.",
        # Day-relative claims need no clock literal.
        "It's Saturday there right now.",
        "It is Monday in Sydney already.",
        "The date today is August 29, 2026.",
    ],
)
def test_blocks_fabricated_current_time_or_date(text):
    assert asserts_current_time_or_date(text) is not None, f"leaked: {text}"


@pytest.mark.parametrize(
    "text",
    [
        # Advice about a time is not a claim about the current time.
        "A good time to sleep is around 11 PM.",
        "Around 11 PM would be sensible.",
        "I would suggest going to bed by 11 PM.",
        # Historical and general knowledge.
        "World War Two ended in 1945.",
        "The Berlin Wall fell in November 1989.",
        "Banks typically open around 9 AM in most countries.",
        "Most people sleep about eight hours a night.",
        "Offices usually close at 5 PM.",
        "Python was released in 1991 by Guido van Rossum.",
        # Reminder confirmations legitimately echo a time back — blocking
        # these would break working functionality.
        "I've set a reminder for 9 PM.",
        "Reminder set for 9:00 PM: call mom.",
        "You have a reminder at 9 PM.",
        "Your reminders are: 5:30 PM take medication.",
        # Ordinary conversation.
        "I am Jarvis, your voice assistant.",
        "I can open applications and set reminders for you.",
        "Sure, I can help you with that.",
        REFUSAL,
    ],
)
def test_allows_legitimate_time_bearing_answers(text):
    assert asserts_current_time_or_date(text) is None, f"false positive: {text}"


def test_guard_replaces_both_fields_and_reports_rule():
    spoken, full, rule = guard_response(
        "The time in India is 00:35 AM.", "The time in India is 00:35 AM, roughly."
    )
    assert spoken == REFUSAL and full == REFUSAL
    assert rule is not None


def test_guard_passes_through_safe_text_untouched():
    spoken, full, rule = guard_response("I can help with that.", "I can help with that.")
    assert spoken == "I can help with that." and full == "I can help with that."
    assert rule is None


def test_guard_blocks_when_only_full_text_fabricates():
    spoken, full, rule = guard_response("Sure.", "Sure. It's currently 3:00 AM in Tokyo.")
    assert spoken == REFUSAL and full == REFUSAL
    assert rule is not None


def test_guard_activation_is_logged(caplog):
    with caplog.at_level("WARNING"):
        guard_response("The time in India is 00:35 AM.", "")
    assert "TRUTHFULNESS_GUARD" in caplog.text
