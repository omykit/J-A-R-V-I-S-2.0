from datetime import datetime, timezone

import pytest

from command_service.intents import matches_time
from command_service.timeloc import (
    build_time_response,
    current_time_in,
    display_name,
    extract_location,
    resolve_timezone,
)

# Fixed instant for every time assertion so results never depend on the
# wall clock: 2026-08-29 12:00 UTC.
FROZEN = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)


# ── Explicit city resolution ──

@pytest.mark.parametrize(
    "location,expected",
    [
        ("Tokyo", "Asia/Tokyo"),
        ("London", "Europe/London"),
        ("New York", "America/New_York"),
        ("Paris", "Europe/Paris"),
        ("Kuwait", "Asia/Kuwait"),
        ("Dubai", "Asia/Dubai"),
        ("Singapore", "Asia/Singapore"),
        # Aliases for cities that are not their own IANA zone.
        ("NYC", "America/New_York"),
        ("Mumbai", "Asia/Kolkata"),
        ("Beijing", "Asia/Shanghai"),
    ],
)
def test_resolves_cities_to_iana_zones(location, expected):
    assert resolve_timezone(location) == expected


# ── Country-level resolution ──

@pytest.mark.parametrize(
    "location,expected",
    [
        ("Japan", "Asia/Tokyo"),
        ("England", "Europe/London"),
        ("India", "Asia/Kolkata"),
        ("Germany", "Europe/Berlin"),
        ("Egypt", "Africa/Cairo"),
    ],
)
def test_resolves_countries_to_iana_zones(location, expected):
    assert resolve_timezone(location) == expected


def test_case_and_punctuation_insensitive():
    assert resolve_timezone("tokyo") == "Asia/Tokyo"
    assert resolve_timezone("  TOKYO  ") == "Asia/Tokyo"
    assert resolve_timezone("Tokyo, Japan") == "Asia/Tokyo"


# ── Location extraction from natural phrasing ──

@pytest.mark.parametrize(
    "text,expected",
    [
        ("What time is it in Tokyo?", "Tokyo"),
        ("Tell me the time in London.", "London"),
        ("What is the current time in New York?", "New York"),
        ("Can you tell me what time it is in Japan?", "Japan"),
        ("give me the time in new york right now", "new york"),
        # No location named.
        ("What time is it?", ""),
        ("Give me the time", ""),
        ("What's the time over there?", ""),
    ],
)
def test_extract_location(text, expected):
    assert extract_location(text) == expected


# ── Natural phrasing still routes to the time intent ──

@pytest.mark.parametrize(
    "text",
    [
        "what time is it",
        "what is the current time",
        "tell me the time",
        "give me the time",
        "can you check the time",
        "what time is it in tokyo",
        "tell me the time in london",
        "can you tell me what time it is in japan",
        "what's the time",
    ],
)
def test_time_phrasings_match_the_time_intent(text):
    assert matches_time(text) is True


@pytest.mark.parametrize("text", ["time for lunch", "is it time to go", "set a timer"])
def test_non_time_phrases_do_not_match(text):
    assert matches_time(text) is False


# ── Full responses at a frozen instant ──

def test_explicit_location_reports_that_locations_time():
    result = build_time_response("What time is it in Tokyo?", now=FROZEN)
    # 12:00 UTC is 21:00 in Tokyo (UTC+9).
    assert result.response == "The time in Tokyo is 9:00 PM."
    assert result.zone == "Asia/Tokyo"
    assert result.resolved is True


def test_explicit_location_differs_from_default():
    # The regression this whole change exists for: an explicit location must
    # never be answered with the default zone's time.
    tokyo = build_time_response("What time is it in Tokyo?", now=FROZEN)
    default = build_time_response(
        "What time is it?", default_timezone="Asia/Kuwait", now=FROZEN
    )
    assert tokyo.response != default.response
    assert "9:00 PM" in tokyo.response
    assert "3:00 PM" in default.response  # Kuwait is UTC+3


def test_london_and_new_york_at_the_same_instant():
    london = build_time_response("Tell me the time in London.", now=FROZEN)
    new_york = build_time_response("Give me the time in New York.", now=FROZEN)
    assert london.response == "The time in London is 1:00 PM."  # BST, UTC+1
    assert new_york.response == "The time in New York is 8:00 AM."  # EDT, UTC-4


def test_country_level_request_hedges_but_still_answers():
    result = build_time_response("What time is it in the USA?", now=FROZEN)
    assert result.resolved is True
    assert "depends on the region" in result.response


# ── Default location behaviour ──

def test_configured_default_timezone_is_used_when_no_location_given():
    result = build_time_response(
        "What time is it?", default_timezone="Asia/Kuwait", now=FROZEN
    )
    assert result.response == "The time is 3:00 PM."
    assert result.zone == "Asia/Kuwait"


def test_falls_back_to_geolocation_when_no_default_configured():
    result = build_time_response(
        "What time is it?", geolocate=lambda: "Europe/London", now=FROZEN
    )
    assert result.response == "The time is 1:00 PM."
    assert result.zone == "Europe/London"


def test_configured_default_takes_priority_over_geolocation():
    result = build_time_response(
        "What time is it?",
        default_timezone="Asia/Tokyo",
        geolocate=lambda: "Europe/London",
        now=FROZEN,
    )
    assert result.zone == "Asia/Tokyo"


def test_geolocation_failure_does_not_crash():
    def boom() -> str:
        raise RuntimeError("network down")

    result = build_time_response("What time is it?", geolocate=boom, now=FROZEN)
    assert "The time is" in result.response
    assert result.resolved is True


def test_invalid_configured_timezone_is_ignored():
    result = build_time_response(
        "What time is it?",
        default_timezone="Not/AZone",
        geolocate=lambda: "Asia/Kuwait",
        now=FROZEN,
    )
    assert result.zone == "Asia/Kuwait"


# ── Unknown locations must not silently answer with another zone ──

def test_unknown_location_fails_gracefully():
    result = build_time_response(
        "What time is it in Wakanda?", default_timezone="Asia/Kuwait", now=FROZEN
    )
    assert result.resolved is False
    assert "Wakanda" in result.response
    # Must not leak the default zone's time.
    assert "3:00 PM" not in result.response
    assert ":" not in result.response.replace("Wakanda", "")


def test_unknown_location_never_returns_a_clock_time():
    for place in ["Wakanda", "Narnia", "Atlantis"]:
        result = build_time_response(f"What time is it in {place}?", now=FROZEN)
        assert result.resolved is False
        assert "AM" not in result.response and "PM" not in result.response


# ── Display formatting ──

def test_display_name_titlecases_lowercase_input_but_keeps_user_casing():
    assert display_name("new york") == "New York"
    assert display_name("Tokyo") == "Tokyo"
    assert display_name("usa") == "the USA"


def test_current_time_in_accepts_naive_now_as_utc():
    naive = datetime(2026, 8, 29, 12, 0)
    assert current_time_in("Asia/Tokyo", now=naive).hour == 21
