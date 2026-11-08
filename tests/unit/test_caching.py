"""Tests for caching of brand statistics and its invalidation."""

from collections.abc import Iterator

import pytest

from car_catalog.performance.analytics import CarRecord, brand_statistics, generate_cars
from car_catalog.performance.caching import CachedCarCatalog, brand_cache_info, clear_caches


@pytest.fixture
def catalog() -> Iterator[CachedCarCatalog]:
    clear_caches()  # every test starts with an empty cache
    yield CachedCarCatalog(generate_cars(1_000))
    clear_caches()


def test_second_call_is_a_cache_hit(catalog: CachedCarCatalog) -> None:
    first = catalog.brand_statistics("Toyota")
    second = catalog.brand_statistics(" toyota ")
    assert second is first
    assert brand_cache_info() == (1, 1, 1)


def test_cached_value_is_correct(catalog: CachedCarCatalog) -> None:
    assert catalog.brand_statistics("BMW") == brand_statistics(catalog.cars, "BMW")


def test_update_price_invalidates_cache(catalog: CachedCarCatalog) -> None:
    car = next(car for car in catalog.cars if car.brand == "Tesla")
    before = catalog.brand_statistics("Tesla")
    catalog.update_price(car.car_id, 9_000_000.0)
    after = catalog.brand_statistics("Tesla")
    assert catalog.version == 1
    assert after.max_price == 9_000_000.0
    assert after.average_price > before.average_price
    assert brand_cache_info() == (0, 2, 2)


def test_add_and_remove_invalidate_cache(catalog: CachedCarCatalog) -> None:
    count = catalog.brand_statistics("Skoda").count
    catalog.add(CarRecord(5_001, "Skoda", "Octavia", 2024, 1_200_000.0, 5_000))
    assert catalog.brand_statistics("Skoda").count == count + 1
    catalog.remove(5_001)
    assert catalog.brand_statistics("Skoda").count == count
    assert catalog.version == 2


def test_manufacturer_statistics_are_cached_and_invalidated(catalog: CachedCarCatalog) -> None:
    first = catalog.manufacturer_statistics()
    assert catalog.manufacturer_statistics() is first
    catalog.add(CarRecord(5_001, "Audi", "A4", 2020, 900_000.0, 50_000))
    assert catalog.manufacturer_statistics()["Audi"].count == first["Audi"].count + 1


def test_unknown_brand_gives_empty_statistics(catalog: CachedCarCatalog) -> None:
    assert catalog.brand_statistics("Lada").count == 0


@pytest.mark.parametrize("action", ["update", "remove"])
def test_missing_car_raises_and_keeps_version(catalog: CachedCarCatalog, action: str) -> None:
    with pytest.raises(KeyError, match="999999"):
        if action == "update":
            catalog.update_price(999_999, 1.0)
        else:
            catalog.remove(999_999)
    assert catalog.version == 0


def test_clear_caches_empties_cache(catalog: CachedCarCatalog) -> None:
    catalog.brand_statistics("Audi")
    clear_caches()
    assert brand_cache_info() == (0, 0, 0)
