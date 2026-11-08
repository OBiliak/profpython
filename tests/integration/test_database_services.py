"""Integration tests: service layer (functions of laboratory work 1, SQL aggregates, transactions)."""

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from car_catalog.persistence.exceptions import PriceUpdateError
from car_catalog.persistence.repositories import CarRepository
from car_catalog.persistence.services import (
    CarCatalogService,
    ManufacturerStatistics,
    update_prices_for_manufacturer,
)

pytestmark = pytest.mark.integration


def prices(session: Session, brand: str) -> list[float]:
    """Prices of one brand read from the database."""
    return [car.price for car in CarRepository(session).find_by_brand(brand)]


# --- Functions of laboratory work 1 and aggregates ---


def test_most_expensive_car(seeded_session: Session) -> None:
    car = CarCatalogService(seeded_session).get_most_expensive()

    assert car is not None and (car.brand, car.model) == ("BMW", "X5")


def test_lowest_mileage_car(seeded_session: Session) -> None:
    car = CarCatalogService(seeded_session).get_lowest_mileage()

    assert car is not None and (car.brand, car.model, car.mileage) == ("Toyota", "RAV4", 32_000)


def test_average_count_and_sum(seeded_session: Session) -> None:
    service = CarCatalogService(seeded_session)

    assert service.get_average_price() == pytest.approx(758_000)
    assert service.count_cars() == 10
    assert service.get_total_value() == pytest.approx(7_580_000)


def test_aggregates_of_empty_database(session: Session) -> None:
    service = CarCatalogService(session)

    assert service.get_most_expensive() is None
    assert service.get_lowest_mileage() is None
    assert service.get_average_price() == 0.0
    assert service.count_cars() == 0
    assert service.get_total_value() == 0.0
    assert service.statistics_by_manufacturer() == []


def test_statistics_by_manufacturer_uses_group_by(seeded_session: Session) -> None:
    rows = CarCatalogService(seeded_session).statistics_by_manufacturer()

    assert [row.name for row in rows] == ["BMW", "Toyota", "Volkswagen", "Skoda", "Renault"]
    assert rows[1] == ManufacturerStatistics("Toyota", 3, pytest.approx(883_333.33), 2_650_000)


def test_service_search_and_year_filter(seeded_session: Session) -> None:
    service = CarCatalogService(seeded_session)

    assert [car.model for car in service.find_by_brand("Skoda")] == ["Octavia", "Fabia"]
    assert [car.id for car in service.filter_by_year(2020, 2021)] == [5, 2]


def test_year_filter_rejects_reversed_range(seeded_session: Session) -> None:
    with pytest.raises(ValueError, match="Початковий рік"):
        CarCatalogService(seeded_session).filter_by_year(2022, 2019)


# --- Transaction: bulk price update with commit / rollback ---


def test_bulk_price_update_commits_all_prices(seeded_session: Session) -> None:
    count = update_prices_for_manufacturer(
        seeded_session, "Toyota", {1: 505_000, 2: 1_120_000, 8: 955_000}
    )

    seeded_session.expire_all()
    assert count == 3
    assert prices(seeded_session, "Toyota") == [505_000, 1_120_000, 955_000]


@pytest.mark.parametrize(
    ("manufacturer", "new_prices", "message"),
    [
        ("Volkswagen", {3: 365_000, 9: -1}, "більшою за нуль"),
        ("Volkswagen", {3: 365_000, 9: 0}, "більшою за нуль"),
        ("Volkswagen", {3: 365_000, 999: 500_000}, "ID 999 не знайдено"),
        ("Volkswagen", {3: 365_000, 5: 1_800_000}, "не належить виробнику Volkswagen"),
    ],
    ids=["negative-price", "zero-price", "missing-car", "other-manufacturer"],
)
def test_bulk_price_update_rolls_back_on_incorrect_data(
    seeded_session: Session, manufacturer: str, new_prices: dict[int, float], message: str
) -> None:
    before = prices(seeded_session, "Volkswagen")

    with pytest.raises(PriceUpdateError, match=message):
        update_prices_for_manufacturer(seeded_session, manufacturer, new_prices)

    seeded_session.expire_all()
    assert prices(seeded_session, "Volkswagen") == before == [380_000, 640_000]
    assert prices(seeded_session, "BMW") == [1_890_000, 870_000]


def test_bulk_price_update_of_unknown_manufacturer(seeded_session: Session) -> None:
    with pytest.raises(PriceUpdateError, match="Виробника Tesla не знайдено"):
        update_prices_for_manufacturer(seeded_session, "Tesla", {1: 1.0})


def test_rollback_is_visible_from_another_connection(
    seeded_session: Session, database_path: Path
) -> None:
    """After rollback another connection to the same file sees the old price (Atomicity + Durability)."""
    with pytest.raises(PriceUpdateError):
        update_prices_for_manufacturer(seeded_session, "Volkswagen", {3: 365_000, 9: -1})

    connection = sqlite3.connect(database_path)
    try:
        row = connection.execute("SELECT price FROM cars WHERE id = ?", (3,)).fetchone()
    finally:
        connection.close()
    assert row == (380_000.0,)
