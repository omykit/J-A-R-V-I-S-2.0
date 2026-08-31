"""Emoji stripping, and the cleaner/guard interaction that must not regress.

Two separate concerns live here because they share one root: clean_ai_response
rewrites the text that reaches the speaker, and anything downstream of it has
to account for what it removed.
"""

from ai_service.response_cleaner import clean_ai_response, strip_emoji
from ai_service.truthfulness import REFUSAL, asserts_current_time_or_date, guard_response


# ── Task 5: emoji stripping ─────────────────────────────────────────────
# Piper cannot speak emoji. Nothing else in the pipeline removed them.


def test_emoji_are_stripped_from_a_spoken_answer():
    assert clean_ai_response("Docker is a container platform 🐳") == "Docker is a container platform."


def test_multiple_and_repeated_emoji_are_stripped():
    assert strip_emoji("Hello 👋👋 world 🌍🎉") == "Hello world"


def test_a_compound_emoji_leaves_nothing_behind():
    """Family and profession emoji are several codepoints joined by ZWJ."""
    assert strip_emoji("Hi 👨‍👩‍👧‍👦 there") == "Hi there"


def test_flag_sequences_are_stripped():
    assert strip_emoji("Paris 🇫🇷 is in France") == "Paris is in France"


def test_an_emoji_only_response_becomes_empty():
    """An empty return makes the caller fall back rather than speak nothing."""
    assert clean_ai_response("👍🎉") == ""


def test_ordinary_punctuation_and_symbols_survive():
    """The ranges are tight on purpose: these all sit below U+2600."""
    text = "It is 18 degrees — “mild” – and costs £5 or €6."
    assert strip_emoji(text) == text


def test_degree_and_percent_signs_survive():
    assert strip_emoji("90° and 50% humidity") == "90° and 50% humidity"


def test_stripping_leaves_no_double_spaces():
    assert strip_emoji("Docker 🐳 is 🎉 useful") == "Docker is useful"


def test_text_without_emoji_is_unchanged():
    assert strip_emoji("A plain sentence.") == "A plain sentence."


# ── Task 6: the cleaner/guard interaction ───────────────────────────────


def test_cleaner_removes_the_word_currently():
    """Pins the behaviour the next test depends on. If this ever changes,
    the guard's exposure changes with it."""
    assert "currently" not in clean_ai_response("It is currently 3 PM.").lower()


def test_guard_must_check_full_text_not_only_spoken_text():
    """DO NOT "simplify" guard_response to check spoken_text alone.

    clean_ai_response strips the words "currently" and "right now", and both
    are _CONTEXT_PHRASE markers in truthfulness.py. So a fabricated time
    phrased as "It is currently 3 PM" arrives at the guard already stripped
    down to "It is 3 PM" in spoken_text -- which does NOT match, because the
    clock pattern needs a context marker or a capitalised place beside it.

    It is caught only because guard_response ALSO inspects full_text, which
    is the raw, uncleaned model output. Dropping that second check silently
    reopens the time-fabrication hole with every test still green.
    """
    raw = "It is currently 3 PM."
    spoken = clean_ai_response(raw)

    # The precondition: cleaning has destroyed the evidence.
    assert asserts_current_time_or_date(spoken) is None, (
        "cleaned text no longer looks like a time claim -- this is the trap"
    )
    # The raw text still carries it.
    assert asserts_current_time_or_date(raw) is not None

    # And the guard still blocks the turn, because it checks both.
    guarded_spoken, guarded_full, rule = guard_response(spoken, raw)

    assert rule is not None, "guard failed to fire: full_text check is gone"
    assert guarded_spoken == REFUSAL
    assert guarded_full == REFUSAL


def test_the_same_trap_applies_to_right_now():
    """"right now" is stripped by the cleaner and is also a context marker."""
    raw = "It is 3 PM right now."
    spoken = clean_ai_response(raw)

    assert asserts_current_time_or_date(spoken) is None
    _, _, rule = guard_response(spoken, raw)
    assert rule is not None


def test_a_normal_answer_is_not_blocked_by_either_path():
    raw = "Docker is a container platform."
    spoken = clean_ai_response(raw)

    guarded_spoken, _, rule = guard_response(spoken, raw)

    assert rule is None
    assert guarded_spoken == spoken
