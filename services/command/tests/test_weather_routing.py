"""Weather is routed to the AI service, not answered deterministically.

The WeatherAPI/OpenWeatherMap lookup was removed from the command service.
Weather is still matched at its original position in the routing chain and
then handed to the AI via ai_fallback, rather than the branch being deleted
outright -- see the ordering test at the bottom for why that distinction
matters.
"""

import pytest

WEATHER_UTTERANCES = [
    "what is the weather",
    "what is the weather in Paris",
    "whats the weather like",
    "what is the weather right now",
    "what is the temperature",
    "what is the temperature outside",
    "what is the climate in Tokyo",
    "what is the forecast",
]


@pytest.mark.parametrize("utterance", WEATHER_UTTERANCES)
async def test_weather_is_handed_to_the_ai_service(utterance, client):
    response = await client.post("/execute", json={"text": utterance})
    body = response.json()

    # The gateway forwards to the AI service when handled is false or the
    # action is ai_fallback -- see gateway/router.py.
    assert body["handled"] is False
    assert body["action"] == "ai_fallback"
    assert body["response"] == ""


async def test_no_weather_api_is_called(client, monkeypatch):
    """The deterministic lookup must not run even if a key is configured."""
    from command_service import weather as weather_module

    def fail(*args, **kwargs):
        raise AssertionError("the weather API was called")

    monkeypatch.setattr(weather_module, "get_weather_response", fail)
    monkeypatch.setattr(weather_module, "_read_json", fail)

    response = await client.post("/execute", json={"text": "what is the weather in Paris"})
    assert response.json()["handled"] is False


async def test_weather_still_outranks_the_date_branch(client):
    """Regression guard for how this removal was done.

    Weather was matched before time and date. Deleting the branch outright
    let "what is the weather forecast for the day" fall through to
    matches_date -- which matches the bare word "day" -- and answer with
    today's date instead of reaching the AI at all.
    """
    response = await client.post(
        "/execute", json={"text": "what is the weather forecast for the day"}
    )
    body = response.json()

    assert body["handled"] is False
    assert "date is" not in body["response"]


async def test_time_and_date_are_still_answered_deterministically(client):
    """Removing weather must not disturb its neighbours in the chain."""
    time_body = (await client.post("/execute", json={"text": "what time is it in Paris"})).json()
    date_body = (await client.post("/execute", json={"text": "what is the date"})).json()

    assert time_body["handled"] is True
    assert "The time in Paris is" in time_body["response"]
    assert date_body["handled"] is True
    assert "date is" in date_body["response"]


async def test_location_is_still_answered_deterministically(client, monkeypatch):
    """get_location_response lives in weather.py, which stays."""
    from command_service import handler as handler_module

    monkeypatch.setattr(handler_module, "get_location_response", lambda: "You appear to be in Kuwait.")

    body = (await client.post("/execute", json={"text": "where am i"})).json()
    assert body["handled"] is True
    assert "Kuwait" in body["response"]
