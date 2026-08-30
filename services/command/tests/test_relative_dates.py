"""Relative and timezone-aware date handling.

Two bugs are covered here, both from JHIT session 1 (2026-08-29 23:08-00:12):

1. "what is the date tomorrow" answered "Today's date is ..." (four times).
2. The date was computed from the container clock (UTC) while the user is
   UTC+3, so between 21:00 and midnight local the answer was a day behind.
   The session log shows "Today's date is Saturday, August 29" at local
   00:06 on Sunday the 30th.

Every zone-sensitive test below injects an explicit `now` and an explicit
timezone. The previous version of this file used the host's local clock,
which is exactly why it stayed green while production was a day behind.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from command_service.handler import CommandHandler

KUWAIT = ZoneInfo("Asia/Kuwait")  # UTC+3, the user's zone

# 22:59 UTC on Aug 29 == 01:59 on Sunday Aug 30 in Kuwait.
# This is inside the 21:00-24:00 band where the old code was wrong, and is
# the same wall-clock moment as the session-1 failure.
UTC_INSTANT = datetime(2026, 8, 29, 22, 59, tzinfo=timezone.utc)
KUWAIT_NOW = UTC_INSTANT.astimezone(KUWAIT)


def handler() -> CommandHandler:
    return CommandHandler(memory_client=None)


# ── The regression that matters: zone, not container clock ──

def test_date_uses_user_timezone_not_container_utc():
    """THE session-1 regression. Under UTC this instant is Saturday the
    29th; in the user's zone it is Sunday the 30th. Answering "Saturday"
    here is the exact bug."""
    result = handler()._handle_date_request("what is the date", now=KUWAIT_NOW)
    assert result.response == "Today's date is Sunday, August 30, 2026."
    assert "Saturday, August 29" not in result.response  # the UTC answer


def test_tomorrow_offsets_from_zone_aware_now():
    result = handler()._handle_date_request("what is the date tomorrow", now=KUWAIT_NOW)
    assert result.response == "Tomorrow's date is Monday, August 31, 2026."


def test_yesterday_offsets_from_zone_aware_now():
    result = handler()._handle_date_request("what was the date yesterday", now=KUWAIT_NOW)
    assert result.response == "Yesterday's date was Saturday, August 29, 2026."


@pytest.mark.parametrize(
    "zone_name,expected_day",
    [
        ("Asia/Kuwait", "Sunday, August 30, 2026"),    # UTC+3 -> already the 30th
        ("UTC", "Saturday, August 29, 2026"),          # UTC    -> still the 29th
        ("America/Chicago", "Saturday, August 29, 2026"),  # UTC-5 -> still the 29th
        ("Asia/Tokyo", "Sunday, August 30, 2026"),     # UTC+9 -> already the 30th
    ],
)
def test_same_instant_yields_different_dates_per_zone(zone_name, expected_day):
    """Proves the date genuinely follows the configured zone."""
    local_now = UTC_INSTANT.astimezone(ZoneInfo(zone_name))
    result = handler()._handle_date_request("what is the date", now=local_now)
    assert result.response == f"Today's date is {expected_day}."


# ── Relative modifiers ──

@pytest.mark.parametrize(
    "text,offset,label",
    [
        ("what is the date tomorrow", 1, "Tomorrow's date is"),
        ("whats the date tomorrow", 1, "Tomorrow's date is"),
        ("what is tomorrow's date", 1, "Tomorrow's date is"),
        ("what was the date yesterday", -1, "Yesterday's date was"),
        ("what was yesterday's date", -1, "Yesterday's date was"),
        ("what is today's date", 0, "Today's date is"),
        ("what day is it", 0, "Today's date is"),
    ],
)
def test_relative_modifiers(text, offset, label):
    result = handler()._handle_date_request(text, now=KUWAIT_NOW)
    expected = (KUWAIT_NOW + timedelta(days=offset)).strftime("%A, %B %d, %Y")
    assert result.response == f"{label} {expected}."


@pytest.mark.parametrize(
    "text",
    [
        "what is the date next friday",
        "what was the date last monday",
        "what is the date in 3 days",
        "what is the date 5 days from now",
    ],
)
def test_unhandled_modifier_refuses_instead_of_answering_for_today(text):
    result = handler()._handle_date_request(text, now=KUWAIT_NOW)
    assert "rather not guess" in result.response
    assert not result.response.startswith("Today's date is")


# ── Through the real HTTP endpoint (wiring check) ──

async def test_date_endpoint_is_wired_and_handled(client):
    response = await client.post("/execute", json={"text": "what is the date tomorrow"})
    assert response.status_code == 200
    body = response.json()
    assert body["handled"] is True
    assert body["response"].startswith("Tomorrow's date is")


async def test_unhandled_modifier_refuses_via_endpoint(client):
    response = await client.post("/execute", json={"text": "what is the date next friday"})
    body = response.json()
    assert body["handled"] is True
    assert "rather not guess" in body["response"]


# ── The resolver itself (the part that was actually broken) ──

def test_zone_aware_now_follows_configured_timezone(monkeypatch):
    """_zone_aware_now must return the user's wall clock, not the
    container's. Injected `now` in the tests above exercises the offset
    logic; this exercises the resolution that was the real defect."""
    from command_service import handler as handler_module

    monkeypatch.setattr(handler_module.settings, "default_timezone", "Asia/Tokyo")
    result = handler()._zone_aware_now()
    assert result.tzinfo is not None, "must be timezone-aware, not naive"
    assert "Tokyo" in str(result.tzinfo)


def test_zone_aware_now_is_never_naive_utc(monkeypatch):
    from command_service import handler as handler_module

    monkeypatch.setattr(handler_module.settings, "default_timezone", "Asia/Kuwait")
    now_kuwait = handler()._zone_aware_now()
    assert now_kuwait.utcoffset() is not None
    assert now_kuwait.utcoffset().total_seconds() == 3 * 3600  # UTC+3
