from memory_service.config import Settings


def test_settings_ignores_other_services_env_vars(monkeypatch):
    # Regression test: all four services read the same shared root .env.
    # Settings() used to raise extra_forbidden when unrelated services' vars
    # (any prefix other than JARVIS_MEMORY_) were present.
    monkeypatch.setenv("JARVIS_AI_MODEL", "not-this-service")
    monkeypatch.setenv("JARVIS_CMD_WEATHER_API_KEY", "not-this-service")
    monkeypatch.setenv("JARVIS_GW_ALLOWED_ORIGINS", "http://example.com")

    settings = Settings()

    assert not hasattr(settings, "model")
    assert not hasattr(settings, "weather_api_key")
    assert not hasattr(settings, "allowed_origins")


def test_settings_still_reads_its_own_env_vars(monkeypatch):
    monkeypatch.setenv("JARVIS_MEMORY_ECHO_SQL", "true")
    settings = Settings()
    assert settings.echo_sql is True
