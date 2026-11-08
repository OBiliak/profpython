"""Tests for the settings from environment variables (pydantic-settings)."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from pydantic import ValidationError

from car_catalog.config import Settings, get_settings
from car_catalog.persistence.database import database_url

VARIABLES = (
    "APP_NAME",
    "ENVIRONMENT",
    "DATABASE_URL",
    "LOG_LEVEL",
    "HOST",
    "PORT",
    "SEED_DEMO_DATA",
)


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """No settings from the shell of the developer; the cached settings are read again."""
    for name in VARIABLES:
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_default_settings() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.environment in {"development", "test", "production"}
    assert settings.environment == "development"
    assert settings.database_url == "sqlite:///car_catalog.db"
    assert settings.log_level == "INFO"
    assert (settings.host, settings.port, settings.seed_demo_data) == ("127.0.0.1", 8000, False)


def test_environment_variables_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite:////app/data/car_catalog.db")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("PORT", "8080")
    monkeypatch.setenv("SEED_DEMO_DATA", "true")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.environment == "production"
    assert settings.database_url == "sqlite:////app/data/car_catalog.db"
    assert settings.log_level == "DEBUG"
    assert settings.port == 8080
    assert settings.seed_demo_data is True


def test_env_file_is_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("ENVIRONMENT=test\nLOG_LEVEL=WARNING\n", encoding="utf-8")
    monkeypatch.setenv("LOG_LEVEL", "ERROR")  # the environment is stronger than .env
    settings = Settings(_env_file=env_file)  # type: ignore[call-arg]
    assert settings.environment == "test"
    assert settings.log_level == "ERROR"


@pytest.mark.parametrize(
    ("name", "value"), [("ENVIRONMENT", "staging"), ("LOG_LEVEL", "VERBOSE"), ("PORT", "eighty")]
)
def test_invalid_value_is_rejected(monkeypatch: pytest.MonkeyPatch, name: str, value: str) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_get_settings_is_cached_and_used_by_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///first.db")
    assert get_settings() is get_settings()
    assert database_url() == "sqlite:///first.db"
    monkeypatch.setenv("DATABASE_URL", "sqlite:///second.db")
    assert database_url() == "sqlite:///first.db"  # read once
    get_settings.cache_clear()
    assert database_url() == "sqlite:///second.db"


def test_env_example_lists_required_variables_without_secrets() -> None:
    text = (Path(__file__).resolve().parents[2] / ".env.example").read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line and not line.startswith("#")]
    names = [line.split("=", 1)[0] for line in lines]
    assert {"DATABASE_URL", "ENVIRONMENT", "LOG_LEVEL"} <= set(names)
    for name in names:
        assert not any(word in name for word in ("PASSWORD", "TOKEN", "SECRET", "KEY"))
