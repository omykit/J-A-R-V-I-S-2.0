import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


def _read_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "JarvisDesktop/2.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        return json.loads(response.read().decode("utf-8"))


location_cache: dict | None = None


def get_location_data() -> dict:
    global location_cache
    if location_cache is not None:
        return location_cache

    providers = [
        "https://ipapi.co/json/",
        "https://ipwho.is/",
    ]
    for url in providers:
        try:
            data = _read_json(url)
        except Exception:
            continue

        latitude = data.get("latitude")
        longitude = data.get("longitude")
        if latitude is None or longitude is None:
            continue

        # Both providers return an IANA timezone; ipapi.co as a string,
        # ipwho.is nested under "timezone". Used by timeloc for the default
        # timezone when a time request names no location.
        tz = data.get("timezone")
        if isinstance(tz, dict):
            tz = tz.get("id")

        location_cache = {
            "city": data.get("city") or data.get("region") or "your area",
            "region": data.get("region") or "",
            "country": data.get("country_name") or data.get("country") or "",
            "latitude": latitude,
            "longitude": longitude,
            "timezone": str(tz or ""),
        }
        return location_cache

    raise RuntimeError("I could not determine your location right now.")


def get_local_timezone() -> str:
    """IANA timezone for the service's apparent location, or "" if unknown."""
    try:
        return str(get_location_data().get("timezone") or "")
    except Exception:
        return ""


def get_location_response() -> str:
    try:
        location = get_location_data()
    except Exception as exc:
        return str(exc)

    parts = [location.get("city", ""), location.get("region", ""), location.get("country", "")]
    label = ", ".join(part for part in parts if part)
    return f"You appear to be in {label or 'your current area'}."


def extract_weather_query(raw_text: str, normalized_text: str) -> str:
    text = " ".join(normalized_text.strip().split())
    candidate = ""
    for separator in (" in ", " at ", " for "):
        if separator in text:
            candidate = text.rsplit(separator, 1)[-1].strip()
            break
    if not candidate:
        return ""

    candidate = re.sub(r"\b(today|right now|now|outside|currently|please)\b", " ", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"\s+", " ", candidate).strip(" .,!?")
    if candidate in {"", "today", "outside", "right now", "now"}:
        return ""
    return candidate


def _resolve_weather_lookup_target(explicit_query: str) -> tuple[str, dict | None]:
    if explicit_query:
        return explicit_query, None
    location = get_location_data()
    latitude = location.get("latitude")
    longitude = location.get("longitude")
    if latitude is not None and longitude is not None:
        return f"{latitude},{longitude}", location
    city = str(location.get("city") or "").strip()
    if city:
        return city, location
    raise RuntimeError("I couldn't determine a weather location right now.")


def _read_http_error_payload(exc: urllib.error.HTTPError) -> tuple[int, str]:
    try:
        payload = exc.read().decode("utf-8", errors="replace")
        data = json.loads(payload)
        error = data.get("error", {}) if isinstance(data, dict) else {}
        code = int(error.get("code") or data.get("code") or 0)
        message = str(error.get("message") or data.get("message") or payload).strip()
        return code, message
    except Exception:
        return 0, ""


def get_weatherapi_response(api_key: str, explicit_query: str) -> str:
    try:
        query_value, location = _resolve_weather_lookup_target(explicit_query)
        query = urllib.parse.urlencode({"key": api_key, "q": query_value, "aqi": "no"})
        data = _read_json(f"https://api.weatherapi.com/v1/current.json?{query}")
    except urllib.error.HTTPError as exc:
        service_code, service_message = _read_http_error_payload(exc)
        if service_code == 1006:
            place = explicit_query or "that location"
            return f"I couldn't find a weather match for {place}. Try the city name again."
        if exc.code in {401, 403} or service_code in {2006, 2007, 2008, 2009}:
            return "The weather service rejected the request. Please check your WeatherAPI key."
        return "The weather service could not complete that weather request right now."
    except Exception:
        return "I couldn't reach the weather service right now."

    current = data.get("current", {}) if isinstance(data, dict) else {}
    location_data = data.get("location", {}) if isinstance(data, dict) else {}
    condition = current.get("condition", {}) if isinstance(current, dict) else {}
    temp = current.get("temp_c")
    feels_like = current.get("feelslike_c")
    city = location_data.get("name") or explicit_query or (location or {}).get("city") or "your area"
    if temp is None:
        return f"I reached the weather service, but it did not return a usable temperature for {city}."
    weather_text = condition.get("text") or "current conditions"
    return f"Right now in {city}, the weather is {weather_text} with a temperature of {round(temp)} degrees Celsius and feels like {round(feels_like if feels_like is not None else temp)} degrees."


def get_openweather_response(api_key: str, explicit_query: str) -> str:
    try:
        query_value, location = _resolve_weather_lookup_target(explicit_query)
        if explicit_query:
            query = urllib.parse.urlencode({"q": query_value, "appid": api_key, "units": "metric"})
        else:
            latitude, longitude = str(query_value).split(",", 1)
            query = urllib.parse.urlencode({"lat": latitude, "lon": longitude, "appid": api_key, "units": "metric"})
        data = _read_json(f"https://api.openweathermap.org/data/2.5/weather?{query}")
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            return "The weather service rejected the request. Please check your OpenWeatherMap API key."
        return "The weather service could not complete that weather request right now."
    except Exception:
        return "I couldn't reach the weather service right now."

    weather_list = data.get("weather", [{}])
    weather_desc = weather_list[0].get("description", "current conditions") if weather_list else "current conditions"
    main = data.get("main", {})
    temp = main.get("temp")
    feels_like = main.get("feels_like")
    city = data.get("name") or explicit_query or (location or {}).get("city") or "your area"
    if temp is None:
        return f"I reached the weather service, but it did not return a usable temperature for {city}."
    return f"Right now in {city}, the weather is {weather_desc} with a temperature of {round(temp)} degrees Celsius and feels like {round(feels_like if feels_like is not None else temp)} degrees."


def get_weather_response(raw_text: str, normalized_text: str, weather_api_key: str, openweather_api_key: str) -> str:
    explicit_query = extract_weather_query(raw_text, normalized_text)
    if weather_api_key:
        return get_weatherapi_response(weather_api_key, explicit_query)
    if openweather_api_key:
        return get_openweather_response(openweather_api_key, explicit_query)
    return "Add a weather API key in jarvis_config.json to enable weather updates."
