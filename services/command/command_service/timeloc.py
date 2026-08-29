"""Location -> IANA timezone resolution for time requests.

Kept out of handler.py so the command handler stays a readable list of
intent branches. Resolution is layered:

    explicit location in the request
        -> curated country/city aliases
        -> IANA zone city segments (Asia/Tokyo -> "tokyo")
    no location given
        -> configured default timezone (JARVIS_CMD_DEFAULT_TIMEZONE)
        -> IP geolocation (reuses weather.get_location_data)
        -> the service's own local time
    location given but unresolvable
        -> no time at all; ask the user to rephrase

That last case matters: answering "what time is it in Wakanda?" with some
other zone's time is a confidently-wrong answer, which is worse than
admitting the location wasn't understood.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

# IANA ids are Area/City, so most cities resolve straight from the zone list
# (see _city_index). Countries generally do not, so they're mapped here.
_COUNTRY_ALIASES: dict[str, str] = {
    "japan": "Asia/Tokyo",
    "united kingdom": "Europe/London",
    "uk": "Europe/London",
    "england": "Europe/London",
    "britain": "Europe/London",
    "great britain": "Europe/London",
    "scotland": "Europe/London",
    "wales": "Europe/London",
    "ireland": "Europe/Dublin",
    "france": "Europe/Paris",
    "germany": "Europe/Berlin",
    "spain": "Europe/Madrid",
    "italy": "Europe/Rome",
    "netherlands": "Europe/Amsterdam",
    "holland": "Europe/Amsterdam",
    "belgium": "Europe/Brussels",
    "portugal": "Europe/Lisbon",
    "greece": "Europe/Athens",
    "turkey": "Europe/Istanbul",
    "russia": "Europe/Moscow",
    "ukraine": "Europe/Kyiv",
    "poland": "Europe/Warsaw",
    "sweden": "Europe/Stockholm",
    "norway": "Europe/Oslo",
    "denmark": "Europe/Copenhagen",
    "finland": "Europe/Helsinki",
    "switzerland": "Europe/Zurich",
    "austria": "Europe/Vienna",
    "czechia": "Europe/Prague",
    "czech republic": "Europe/Prague",
    "hungary": "Europe/Budapest",
    "romania": "Europe/Bucharest",
    "india": "Asia/Kolkata",
    "pakistan": "Asia/Karachi",
    "bangladesh": "Asia/Dhaka",
    "sri lanka": "Asia/Colombo",
    "nepal": "Asia/Kathmandu",
    "china": "Asia/Shanghai",
    "hong kong": "Asia/Hong_Kong",
    "taiwan": "Asia/Taipei",
    "south korea": "Asia/Seoul",
    "korea": "Asia/Seoul",
    "thailand": "Asia/Bangkok",
    "vietnam": "Asia/Ho_Chi_Minh",
    "philippines": "Asia/Manila",
    "indonesia": "Asia/Jakarta",
    "malaysia": "Asia/Kuala_Lumpur",
    "uae": "Asia/Dubai",
    "united arab emirates": "Asia/Dubai",
    "emirates": "Asia/Dubai",
    "saudi arabia": "Asia/Riyadh",
    "saudi": "Asia/Riyadh",
    "iran": "Asia/Tehran",
    "iraq": "Asia/Baghdad",
    "israel": "Asia/Jerusalem",
    "jordan": "Asia/Amman",
    "lebanon": "Asia/Beirut",
    "egypt": "Africa/Cairo",
    "south africa": "Africa/Johannesburg",
    "nigeria": "Africa/Lagos",
    "kenya": "Africa/Nairobi",
    "morocco": "Africa/Casablanca",
    "new zealand": "Pacific/Auckland",
    "argentina": "America/Argentina/Buenos_Aires",
    "colombia": "America/Bogota",
    "peru": "America/Lima",
    "venezuela": "America/Caracas",
    # Countries spanning several zones: map to the most commonly meant one.
    # is_approximate() flags these so the reply can hedge instead of
    # implying the whole country shares one clock.
    "usa": "America/New_York",
    "us": "America/New_York",
    "u.s.": "America/New_York",
    "united states": "America/New_York",
    "america": "America/New_York",
    "canada": "America/Toronto",
    "australia": "Australia/Sydney",
    "brazil": "America/Sao_Paulo",
    "mexico": "America/Mexico_City",
    "chile": "America/Santiago",
}

# Countries above whose zone is one of several — the reply hedges for these.
_MULTI_ZONE_COUNTRIES = frozenset(
    {
        "usa",
        "us",
        "u.s.",
        "united states",
        "america",
        "canada",
        "australia",
        "brazil",
        "mexico",
        "russia",
        "indonesia",
        "chile",
    }
)

# Cities that are not their own IANA zone, plus common short forms.
_CITY_ALIASES: dict[str, str] = {
    "nyc": "America/New_York",
    "new york city": "America/New_York",
    "manhattan": "America/New_York",
    "la": "America/Los_Angeles",
    "los angeles": "America/Los_Angeles",
    "sf": "America/Los_Angeles",
    "san francisco": "America/Los_Angeles",
    "silicon valley": "America/Los_Angeles",
    "seattle": "America/Los_Angeles",
    "washington dc": "America/New_York",
    "washington d.c.": "America/New_York",
    "dc": "America/New_York",
    "boston": "America/New_York",
    "philadelphia": "America/New_York",
    "atlanta": "America/New_York",
    "miami": "America/New_York",
    "austin": "America/Chicago",
    "dallas": "America/Chicago",
    "houston": "America/Chicago",
    "mumbai": "Asia/Kolkata",
    "bombay": "Asia/Kolkata",
    "delhi": "Asia/Kolkata",
    "new delhi": "Asia/Kolkata",
    "bangalore": "Asia/Kolkata",
    "bengaluru": "Asia/Kolkata",
    "hyderabad": "Asia/Kolkata",
    "chennai": "Asia/Kolkata",
    "beijing": "Asia/Shanghai",
    "peking": "Asia/Shanghai",
    "shenzhen": "Asia/Shanghai",
    "guangzhou": "Asia/Shanghai",
    "saigon": "Asia/Ho_Chi_Minh",
    "abu dhabi": "Asia/Dubai",
    "mecca": "Asia/Riyadh",
    "medina": "Asia/Riyadh",
    "jeddah": "Asia/Riyadh",
    "geneva": "Europe/Zurich",
    "munich": "Europe/Berlin",
    "frankfurt": "Europe/Berlin",
    "hamburg": "Europe/Berlin",
    "barcelona": "Europe/Madrid",
    "milan": "Europe/Rome",
    "florence": "Europe/Rome",
    "venice": "Europe/Rome",
    "st petersburg": "Europe/Moscow",
    "melbourne": "Australia/Melbourne",
    "cape town": "Africa/Johannesburg",
    "rio": "America/Sao_Paulo",
    "rio de janeiro": "America/Sao_Paulo",
    "silicon roundabout": "Europe/London",
}

# How to say a location back when title-casing the raw text reads wrong.
_DISPLAY_OVERRIDES: dict[str, str] = {
    "usa": "the USA",
    "us": "the US",
    "u.s.": "the US",
    "united states": "the United States",
    "uk": "the UK",
    "united kingdom": "the UK",
    "uae": "the UAE",
    "united arab emirates": "the UAE",
    "nyc": "New York City",
    "la": "Los Angeles",
    "sf": "San Francisco",
    "dc": "Washington, D.C.",
    "washington dc": "Washington, D.C.",
}

# Phrases that follow "in"/"at" but name no real place — treat as "no
# location given" rather than as an unresolvable one.
_VAGUE_LOCATIONS = frozenset(
    {
        "",
        "there",
        "here",
        "over there",
        "over here",
        "my area",
        "my location",
        "my time zone",
        "my timezone",
        "this area",
        "the moment",
        "the morning",
        "the afternoon",
        "the evening",
        "the night",
        "general",
        "fact",
        "total",
    }
)

# Legacy/grouping zone prefixes that shouldn't seed the city index.
_LEGACY_AREAS = frozenset({"Etc", "SystemV", "US", "Canada", "Brazil", "Mexico", "Chile"})

_TRAILING_FILLER = re.compile(
    r"\b(please|right now|now|today|currently|at the moment|for me|thanks|thank you|jarvis)\b",
    re.IGNORECASE,
)

_LOCATION_PATTERN = re.compile(r"\b(?:in|at|for)\s+(.+)$", re.IGNORECASE)

_city_index_cache: dict[str, str] | None = None


@dataclass
class TimeResult:
    """A spoken answer for a time request."""

    response: str
    focus_text: str | None = None
    resolved: bool = True
    zone: str | None = None


def _city_index() -> dict[str, str]:
    """Map lowercase city names to IANA ids, derived from the zone list itself."""
    global _city_index_cache
    if _city_index_cache is None:
        index: dict[str, str] = {}
        for zone in sorted(available_timezones()):
            if "/" not in zone:
                continue  # legacy single-word aliases: "Japan", "GB", "Egypt"
            if zone.split("/", 1)[0] in _LEGACY_AREAS:
                continue
            city = zone.rsplit("/", 1)[-1].replace("_", " ").lower()
            index.setdefault(city, zone)  # sorted() keeps collisions deterministic
        _city_index_cache = index
    return _city_index_cache


def normalize_location(value: str) -> str:
    """Lowercase a location for lookup, dropping punctuation and filler."""
    text = " ".join(str(value or "").lower().split())
    text = _TRAILING_FILLER.sub(" ", text)
    text = re.sub(r"[^\w\s.'-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" .,'-")
    # "the USA" / "the UK" should look up the same as "usa" / "uk".
    return re.sub(r"^the\s+", "", text)


def extract_location(text: str) -> str:
    """Pull the location out of a time request, preserving original casing."""
    collapsed = " ".join(str(text or "").strip().split())
    match = _LOCATION_PATTERN.search(collapsed)
    if not match:
        return ""
    candidate = _TRAILING_FILLER.sub(" ", match.group(1))
    candidate = re.sub(r"[^\w\s,.'-]", " ", candidate)
    candidate = re.sub(r"\s+", " ", candidate).strip(" ,.'-")
    if normalize_location(candidate) in _VAGUE_LOCATIONS:
        return ""
    return candidate


def resolve_timezone(location: str) -> str | None:
    """Resolve a place name to an IANA id, or None if it can't be identified."""
    key = normalize_location(location)
    if not key or key in _VAGUE_LOCATIONS:
        return None

    for candidate in _lookup_candidates(key):
        if candidate in _COUNTRY_ALIASES:
            return _COUNTRY_ALIASES[candidate]
        if candidate in _CITY_ALIASES:
            return _CITY_ALIASES[candidate]
        zone = _city_index().get(candidate)
        if zone is not None:
            return zone
    return None


def _lookup_candidates(key: str) -> list[str]:
    """Progressively simpler forms to try: 'tokyo, japan' -> 'tokyo' -> 'japan'."""
    candidates = [key]
    if "," in key:
        head, _, tail = key.partition(",")
        candidates.extend([head.strip(), tail.strip()])
    elif " " in key:
        # "tokyo japan" — try each half without inventing new orderings.
        words = key.split()
        candidates.append(words[0])
        candidates.append(words[-1])
    return [c for c in candidates if c]


def is_approximate(location: str) -> bool:
    """True when a country spans several zones and the answer is one of them."""
    return normalize_location(location) in _MULTI_ZONE_COUNTRIES


def display_name(location: str) -> str:
    """How to say the location back to the user."""
    key = normalize_location(location)
    if key in _DISPLAY_OVERRIDES:
        return _DISPLAY_OVERRIDES[key]
    cleaned = " ".join(str(location or "").split()).strip(" ,.")
    if any(char.isupper() for char in cleaned):
        return cleaned  # user typed their own casing; keep it
    return cleaned.title()


def current_time_in(zone: str, *, now: datetime | None = None) -> datetime:
    """Current wall-clock time in `zone`. `now` is injectable for tests."""
    reference = now if now is not None else datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    return reference.astimezone(ZoneInfo(zone))


def _speak_clock(moment: datetime) -> str:
    return moment.strftime("%I:%M %p").lstrip("0")


def _valid_zone(zone: str) -> str | None:
    if not zone:
        return None
    try:
        ZoneInfo(zone)
    except (ZoneInfoNotFoundError, ValueError):
        return None
    return zone


def resolve_default_zone(
    *,
    default_timezone: str = "",
    geolocate: Callable[[], str] | None = None,
) -> str | None:
    """Zone to use when the request names no location."""
    configured = _valid_zone(default_timezone.strip())
    if configured:
        return configured
    if geolocate is not None:
        try:
            return _valid_zone(str(geolocate() or "").strip())
        except Exception:
            return None
    return None


def build_time_response(
    text: str,
    *,
    default_timezone: str = "",
    now: datetime | None = None,
    geolocate: Callable[[], str] | None = None,
) -> TimeResult:
    """Answer a time request, honouring any location the user named."""
    location = extract_location(text)

    if location:
        zone = resolve_timezone(location)
        if zone is None:
            # Never fall back to another zone here — a wrong time stated
            # confidently is worse than saying the place wasn't understood.
            spoken = display_name(location)
            return TimeResult(
                response=(
                    f"I couldn't work out which timezone {spoken} is in, "
                    "so I'd rather not guess. Try a city or country name."
                ),
                focus_text=f"Unresolved location: {spoken}",
                resolved=False,
            )
        moment = current_time_in(zone, now=now)
        spoken = display_name(location)
        if is_approximate(location):
            return TimeResult(
                response=f"In {spoken} it depends on the region, but in {moment.tzname() or zone} it's {_speak_clock(moment)}.",
                focus_text=f"Timezone: {zone}",
                zone=zone,
            )
        return TimeResult(
            response=f"The time in {spoken} is {_speak_clock(moment)}.",
            focus_text=f"Timezone: {zone}",
            zone=zone,
        )

    zone = resolve_default_zone(default_timezone=default_timezone, geolocate=geolocate)
    if zone is not None:
        moment = current_time_in(zone, now=now)
        return TimeResult(
            response=f"The time is {_speak_clock(moment)}.",
            focus_text=f"Timezone: {zone}",
            zone=zone,
        )

    # No configured default and no geolocation — fall back to local time.
    moment = now.astimezone() if now is not None else datetime.now()
    return TimeResult(response=f"The time is {_speak_clock(moment)}.")
