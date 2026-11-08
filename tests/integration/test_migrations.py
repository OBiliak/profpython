"""Integration tests: Alembic migrations on a separate test database."""

import sqlite3
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext

from car_catalog.persistence.database import create_database_engine
from car_catalog.persistence.migrations import current_revision, downgrade_database, upgrade_database
from car_catalog.persistence.models import Base

pytestmark = pytest.mark.integration


def columns(database_path: Path, table: str) -> list[str]:
    """Column names of a table (PRAGMA table_info)."""
    connection = sqlite3.connect(database_path)
    try:
        return [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]
    finally:
        connection.close()


def test_upgrade_head_creates_tables_and_vin(tmp_path: Path) -> None:
    path = tmp_path / "migrated.db"
    url = f"sqlite:///{path}"

    upgrade_database(url)

    engine = create_database_engine(url)
    assert current_revision(engine) == "0002"
    assert columns(path, "cars") == ["id", "model", "year", "price", "mileage", "manufacturer_id", "vin"]
    assert columns(path, "manufacturers") == ["id", "name", "country"]
    engine.dispose()


def test_migrated_schema_matches_orm_models(tmp_path: Path) -> None:
    """The same check as `alembic check`: no difference between migrations and models."""
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    upgrade_database(url)
    engine = create_database_engine(url)

    with engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)

    engine.dispose()
    assert differences == []


def test_vin_index_is_unique_after_migration(tmp_path: Path) -> None:
    path = tmp_path / "migrated.db"
    upgrade_database(f"sqlite:///{path}")
    connection = sqlite3.connect(path)
    try:
        connection.execute("INSERT INTO manufacturers (name, country) VALUES (?, ?)", ("Toyota", "Японія"))
        insert = "INSERT INTO cars (model, year, price, mileage, manufacturer_id, vin) VALUES (?, ?, ?, ?, ?, ?)"
        connection.execute(insert, ("Corolla", 2018, 520_000, 85_000, 1, "JTDBR32E720000001"))
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE constraint failed: cars.vin"):
            connection.execute(insert, ("Camry", 2019, 980_000, 61_000, 1, "JTDBR32E720000001"))
    finally:
        connection.close()


def test_downgrade_removes_vin_and_upgrade_returns_it(tmp_path: Path) -> None:
    path = tmp_path / "migrated.db"
    url = f"sqlite:///{path}"
    upgrade_database(url)

    downgrade_database(url, "0001")
    assert "vin" not in columns(path, "cars")

    upgrade_database(url)
    assert "vin" in columns(path, "cars")


def test_downgrade_base_drops_all_tables(tmp_path: Path) -> None:
    path = tmp_path / "migrated.db"
    url = f"sqlite:///{path}"
    upgrade_database(url)

    downgrade_database(url, "base")

    engine = create_database_engine(url)
    assert current_revision(engine) is None
    engine.dispose()
    assert columns(path, "cars") == []
