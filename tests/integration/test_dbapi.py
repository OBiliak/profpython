"""Integration tests: Python DB-API (sqlite3) parameterized queries on the test database."""

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from car_catalog.persistence.dbapi import count_cars_by_country, find_cars_by_manufacturer

pytestmark = pytest.mark.integration


def test_find_cars_by_manufacturer(seeded_session: Session, database_path: Path) -> None:
    rows = find_cars_by_manufacturer(str(database_path), "skoda")

    assert rows == [
        (4, "Skoda", "Octavia", 2019, 610_000.0, 67_000),
        (7, "Skoda", "Fabia", 2016, 330_000.0, 110_000),
    ]


@pytest.mark.parametrize(
    "malicious",
    ["Toyota' OR '1'='1", "Toyota'; DROP TABLE cars; --"],
    ids=["or-true", "drop-table"],
)
def test_parameter_is_not_part_of_sql(seeded_session: Session, database_path: Path, malicious: str) -> None:
    assert find_cars_by_manufacturer(str(database_path), malicious) == []
    assert len(find_cars_by_manufacturer(str(database_path), "Toyota")) == 3


def test_count_cars_by_country(seeded_session: Session, database_path: Path) -> None:
    rows = count_cars_by_country(str(database_path))

    assert rows == [("Німеччина", 4), ("Японія", 3), ("Чехія", 2), ("Франція", 1)]
