from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    memory_service_url: str = "http://localhost:8001"
    weather_api_key: str = ""
    openweather_api_key: str = ""
    # IANA id (e.g. "Asia/Kuwait") used for time requests that name no
    # location. Left empty by default so the location is discovered from IP
    # geolocation instead of being baked in for one particular user.
    default_timezone: str = ""

    # extra="ignore": see services/memory/memory_service/config.py for why
    # (shared root .env across all four services).
    model_config = SettingsConfigDict(env_prefix="JARVIS_CMD_", env_file=".env", extra="ignore")

settings = Settings()
