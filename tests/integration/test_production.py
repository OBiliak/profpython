"""Integration tests of laboratory work 10: GET /health and the production entry point main()."""

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from car_catalog import __version__, main
from car_catalog.api import app, get_session
from car_catalog.config import get_settings
from car_catalog.persistence.database import create_database_engine, create_session_factory
from car_catalog.persistence.repositories import CarRepository

pytestmark = pytest.mark.integration


def test_health_returns_ok(api_client: TestClient) -> None:
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "environment": get_settings().environment,
        "version": __version__,
        "database": "ok",
    }


def test_health_shows_environment_from_settings(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    get_settings.cache_clear()
    try:
        assert api_client.get("/health").json()["environment"] == "production"
    finally:
        get_settings.cache_clear()


def test_health_is_503_when_database_is_unavailable(api_client: TestClient, tmp_path: Path) -> None:
    broken_engine = create_database_engine(f"sqlite:///{tmp_path}/missing/dir/catalog.db")

    def broken_session() -> Iterator[Session]:
        with create_session_factory(broken_engine)() as session:
            yield session

    app.dependency_overrides[get_session] = broken_session
    response = api_client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"error": "service_unavailable", "detail": "База даних недоступна"}


def test_health_is_in_openapi(api_client: TestClient) -> None:
    assert "/health" in api_client.get("/openapi.json").json()["paths"]


@pytest.fixture
def production_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Settings of main() from environment variables: a database file in tmp_path."""
    database = tmp_path / "data" / "car_catalog.db"
    database.parent.mkdir()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database}")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.setenv("PORT", "8080")
    monkeypatch.setenv("SEED_DEMO_DATA", "true")
    get_settings.cache_clear()
    yield database
    get_settings.cache_clear()


def count_cars(database: Path) -> int:
    engine = create_database_engine(f"sqlite:///{database}")
    with create_session_factory(engine)() as session:
        count = len(CarRepository(session).get_all())
    engine.dispose()
    return count


def test_main_migrates_seeds_once_and_starts_uvicorn(
    production_env: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(main.uvicorn, "run", lambda target, **options: calls.append(options))
    assert main.main() == 0
    assert main.main() == 0  # the second start does not add the demo cars again
    log = capsys.readouterr().err
    assert count_cars(production_env) == 10
    assert calls[0] == {"host": "0.0.0.0", "port": 8080, "log_level": "debug", "reload": False}
    assert "INFO car_catalog Starting Car Catalog" in log
    assert "environment=production, log level=DEBUG" in log
    assert "demo cars added: 10" in log
    assert "demo cars added: 0" in log
    assert logging.getLogger().level == logging.DEBUG


def test_main_without_seed_creates_empty_database(
    production_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SEED_DEMO_DATA", "false")
    monkeypatch.setenv("ENVIRONMENT", "development")
    get_settings.cache_clear()
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(main.uvicorn, "run", lambda target, **options: calls.append(options))
    assert main.main() == 0
    assert count_cars(production_env) == 0
    assert calls[0]["reload"] is True
