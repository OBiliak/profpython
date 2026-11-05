"""Unit tests of catalog search, filtering and statistics (CatalogService)."""

import pytest

from car_catalog.domain.exceptions import EmptyCatalogError
from car_catalog.domain.services import CatalogService, MemoryLogger


def ids(vehicles: list) -> list[int]:
    """Return IDs of vehicles in their order."""
    return [vehicle.id for vehicle in vehicles]


def test_finds_vehicles_by_brand_ignoring_case(catalog_service: CatalogService) -> None:
    assert ids(catalog_service.find_by_brand("toyota")) == [1, 2]


def test_find_by_brand_returns_empty_list_for_unknown_brand(
    catalog_service: CatalogService,
) -> None:
    assert catalog_service.find_by_brand("Lada") == []


def test_finds_vehicles_by_part_of_model(catalog_service: CatalogService) -> None:
    assert ids(catalog_service.find_by_model("model")) == [6]


def test_find_by_empty_model_returns_nothing(catalog_service: CatalogService) -> None:
    assert catalog_service.find_by_model("  ") == []


@pytest.mark.parametrize(
    ("min_year", "max_year", "expected"),
    [
        (2019, 2021, [2, 4, 5]),
        (2022, None, [6]),
        (2018, 2018, [1]),
        (2023, None, []),
    ],
    ids=["range", "only-min", "one-year", "no-match"],
)
def test_filters_vehicles_by_year(
    catalog_service: CatalogService,
    min_year: int,
    max_year: int | None,
    expected: list[int],
) -> None:
    assert ids(catalog_service.filter_by_year(min_year, max_year)) == expected


def test_finds_most_expensive_vehicle(catalog_service: CatalogService) -> None:
    vehicle = catalog_service.most_expensive()

    assert (vehicle.brand, vehicle.model) == ("BMW", "X5")


def test_calculates_average_price(catalog_service: CatalogService) -> None:
    average = catalog_service.average_price()

    assert average.amount == pytest.approx(1_124_000)
    assert average.currency == "грн"


def test_finds_vehicle_with_lowest_mileage(catalog_service: CatalogService) -> None:
    assert catalog_service.lowest_mileage().mileage.km == 28_000


@pytest.mark.parametrize("method", ["most_expensive", "lowest_mileage", "average_price"])
def test_statistics_of_empty_catalog_raise_error(
    empty_service: CatalogService, method: str
) -> None:
    with pytest.raises(EmptyCatalogError, match="Каталог порожній"):
        getattr(empty_service, method)()


def test_search_in_empty_catalog_returns_empty_list(empty_service: CatalogService) -> None:
    assert empty_service.find_by_brand("Toyota") == []


def test_adding_vehicle_writes_log_message(
    catalog_service: CatalogService, logger: MemoryLogger
) -> None:
    assert logger.messages[0] == "додано Toyota Corolla (ID 1)"
    assert len(logger.messages) == 5
