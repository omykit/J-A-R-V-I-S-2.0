"""Output-side guard: the AI service must not assert computable facts.

The AI service has no clock and no timezone database, so any current time,
date, or UTC-offset it produces is fabrication. Session 1 (2026-08-29)
produced "The time in India is 00:35 AM" (real answer: 02:05 AM) and, when
challenged, "Yes, I am confident it's currently 00:35 AM in India."

The guard is deliberately on the OUTPUT, not the input. The phrasings that
leaked ("the in india", "what about united") carried no time keyword at all
-- STT had dropped it -- so an input-side keyword filter is blind in exactly
the same way command_service.intents.matches_time is. The output is
detectable no matter how the question was phrased.

Scope is assertions of the CURRENT time/date/offset only. Advice ("a good
time to sleep is around 11 PM"), historical facts, general knowledge, and
reminder confirmations must pass through untouched.

KNOWN CONSTRAINT -- CALENDAR INTEGRATION
    The two-signal rule blocks "clock literal + place marker", which is
    exactly the shape of a calendar event:

        "Your meeting is at 3 PM in London."  ->  BLOCKED

    Calendar integration is on the roadmap. When it lands, EITHER route
    calendar answers through the command service so they never reach this
    guard (the way reminder confirmations already don't), OR add an explicit
    exemption here. Do not discover this as a mystery bug.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

REFUSAL = (
    "I don't have a clock of my own, so I'd rather not guess. "
    'Ask me "what time is it in <city>" and I\'ll look it up properly.'
)

_WEEKDAY = r"monday|tuesday|wednesday|thursday|friday|saturday|sunday"
# A spoken clock value: 00:35 / 11 PM / midnight.
_CLOCK = r"(?:\d{1,2}:\d{2}|\d{1,2}\s*(?:a\.?m\.?|p\.?m\.?)\b|midnight|midday|noon)"
# Hedges the model uses to soften a fabrication -- must not defeat the guard.
_HEDGE = r"(?:currently|probably|likely|roughly|about|around|approximately|maybe|perhaps|now|right\s+now|there)\s+"
_NUMWORD = r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # "Today's date is ..." / "The date today is ..."
    ("today_is", re.compile(
        r"\btoday(?:'s|’s)?\s+(?:date\s+)?is\b|\bthe\s+date\s+today\s+is\b", re.I)),
    # "The current date is Friday, March 3"
    ("current_date_is", re.compile(
        r"\b(?:the\s+)?current\s+(?:date|day|time)\b[^.?!\n]{0,30}?(?:\bis\b|:)", re.I)),
    # "It's Saturday there right now" -- a weekday claim needs no clock literal.
    ("it_is_weekday", re.compile(
        r"\bit(?:'s|’s|\s+is|\s+was|\s+should\s+be|\s+would\s+be|\s+might\s+be"
        r"|\s+may\s+be|\s+could\s+be)\s+(?:" + _HEDGE + r")*(?:" + _WEEKDAY + r")\b", re.I)),
    # "India is about two hours ahead of you" -- a UTC-offset claim is equally
    # fabricated; the model has no timezone data to derive it from.
    ("offset_claim", re.compile(
        r"\b" + _NUMWORD + r"\s*(?:and\s+a\s+half\s+)?hours?\s+(?:ahead|behind|from\s+yours)\b", re.I)),
]

# --- Two-signal rule -------------------------------------------------------
# Matching sentence shapes proved brittle: an adversarial pass defeated an
# earlier shape-based pattern 11 times out of 12 ("The time there is 12:30
# AM.", "Local time is 00:35.", "India: 12:30 AM."). Enumerating phrasings is
# unwinnable, so instead require TWO independent signals:
#
#   1. a clock literal appears at all, AND
#   2. a marker placing it as a CURRENT reading somewhere.
#
# That is what separates a fabrication ("it's 11 PM in India") from the
# legitimate uses that must survive: advice ("around 11 PM"), general
# knowledge ("banks open around 9 AM"), and reminder echoes ("reminder set
# for 9 PM"), none of which carry such a marker.
_CLOCK_RE = re.compile(_CLOCK, re.I)

# Phrase markers are case-insensitive ("The time" / "the time" / "Local time").
_CONTEXT_PHRASE = re.compile(
    r"\b(?:there|here|over\s+there|currently|right\s+now|at\s+the\s+moment"
    r"|local\s+time|your\s+time|their\s+time|the\s+time|the\s+clock"
    r"|clock\s+reads|just\s+turned)\b",
    re.I,
)
# Place markers stay CASE-SENSITIVE so "in most countries" (legitimate general
# knowledge) does not match, while "in India" / "in the United States" does.
_CONTEXT_PLACE = re.compile(
    r"\bin\s+(?:the\s+)?[A-Z][a-zA-Z]+"   # "in India", "in the United States"
    r"|^\s*[A-Z][a-zA-Z]+\s*:",           # "India: 12:30 AM"
    re.M,
)
# A reply that is nothing but a clock value is a time answer by construction.
_BARE_CLOCK = re.compile(
    r"^\W*(?:\d{1,2}:\d{2}(?:\s*[ap]\.?m\.?)?|\d{1,2}\s*[ap]\.?m\.?"
    r"|midnight|midday|noon)\W*$",
    re.I,
)


def asserts_current_time_or_date(text: str) -> str | None:
    """Return the name of the matching rule, or None if the text is safe."""
    if not text:
        return None
    for name, pattern in _PATTERNS:
        if pattern.search(text):
            return name
    if _CLOCK_RE.search(text) and (
        _CONTEXT_PHRASE.search(text) or _CONTEXT_PLACE.search(text)
    ):
        return "clock_with_current_context"
    if _BARE_CLOCK.match(text.strip()):
        return "bare_clock"
    return None


def guard_response(spoken_text: str, full_text: str) -> tuple[str, str, str | None]:
    """Replace fabricated time/date claims with an honest refusal.

    Returns (spoken_text, full_text, rule_name). rule_name is None when
    nothing was blocked. Every activation is logged so session 2 can measure
    how often this fires and whether it over-fires on normal conversation.
    """
    rule = asserts_current_time_or_date(spoken_text) or asserts_current_time_or_date(full_text)
    if rule is None:
        return spoken_text, full_text, None
    logger.warning(
        "TRUTHFULNESS_GUARD fired rule=%s blocked_spoken=%r blocked_full=%r",
        rule, spoken_text, full_text,
    )
    return REFUSAL, REFUSAL, rule
