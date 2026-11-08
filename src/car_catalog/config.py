"""Configuration of the car catalog: constants of the domain and settings from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_YEAR = 1950
MAX_YEAR = 2026
CURRENCY = "грн"


class Settings(BaseSettings):
    """Settings of the application; every field is read from the environment variable of the same name.

    Values are taken from the environment first, then from the .env file, then the defaults below
    are used. The defaults are for local development and contain no secrets.
    """

    app_name: str = "Car Catalog"
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///car_catalog.db"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    host: str = "127.0.0.1"
    port: int = 8000
    seed_demo_data: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Settings are read once and then reused (call get_settings.cache_clear() to read them again)."""
    return Settings()
