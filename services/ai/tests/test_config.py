from ai_service.config import Settings


def test_settings_ignores_other_services_env_vars(monkeypatch):
    # Regression test: all four services read the same shared root .env.
    # Settings() used to raise extra_forbidden when unrelated services' vars
    # (any prefix other than JARVIS_AI_) were present.
    monkeypatch.setenv("JARVIS_MEMORY_DATABASE_URL", "postgresql+asyncpg://not/this-service")
    monkeypatch.setenv("JARVIS_CMD_WEATHER_API_KEY", "not-this-service")
    monkeypatch.setenv("JARVIS_GW_ALLOWED_ORIGINS", "http://example.com")

    settings = Settings()

    assert not hasattr(settings, "database_url")
    assert not hasattr(settings, "weather_api_key")
    assert not hasattr(settings, "allowed_origins")


def test_settings_still_reads_its_own_env_vars(monkeypatch):
    monkeypatch.setenv("JARVIS_AI_MODEL", "custom-model")
    settings = Settings()
    assert settings.model == "custom-model"


def test_system_prompt_states_real_capabilities_and_no_clock_rule():
    """Fix B: the effective prompt is DEFAULT_SYSTEM_PROMPT, not the
    Modelfile SYSTEM block (an /api/chat system message overrides it).
    Session 1 saw the model deny app-launching because the prompt never
    mentioned it. Prompt-only; effectiveness measured in session 2."""
    from ai_service.config import DEFAULT_SYSTEM_PROMPT as p

    lowered = p.lower()
    for capability in ["open desktop apps", "weather", "reminders", "remember personal details"]:
        assert capability in lowered, f"prompt does not mention: {capability}"
    assert "never deny these abilities" in lowered
    assert "cannot observe the present moment" in lowered


def test_system_prompt_permits_historical_dates():
    """Fix B2: the first revision said "never state the current time, date,
    day", which the 3B model over-generalised into refusing "when did the
    Berlin Wall fall?". The rule is now scoped to the present moment and
    history is permitted explicitly."""
    from ai_service.config import DEFAULT_SYSTEM_PROMPT as p

    lowered = p.lower()
    assert "historical dates" in lowered
    assert "answer those normally" in lowered
    assert "right now" in lowered, "refusal must be scoped to the present moment"
