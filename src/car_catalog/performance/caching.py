"""Caching of repeated brand / manufacturer statistics with invalidation after changes."""

from __future__ import annotations

from dataclasses import replace
from functools import lru_cache

from car_catalog.performance.analytics import (
    BrandStatistics,
    CarRecord,
    brand_statistics,
    manufacturer_statistics,
)


class CachedCarCatalog:
    """Catalog whose statistics are cached; every change increases `version`.

    The version is a part of the cache key, so after a change the old results are not used
    (they stay in the LRU cache until it pushes them out).
    """

    def __init__(self, cars: list[CarRecord]) -> None:
        self._cars = list(cars)
        self.version = 0

    @property
    def cars(self) -> list[CarRecord]:
        """Current cars (read only: changes go through the methods below)."""
        return self._cars

    def add(self, car: CarRecord) -> None:
        """Add a car and invalidate the cache."""
        self._cars.append(car)
        self.version += 1

    def update_price(self, car_id: int, price: float) -> None:
        """Change the price of a car and invalidate the cache."""
        for index, car in enumerate(self._cars):
            if car.car_id == car_id:
                self._cars[index] = replace(car, price=price)
                self.version += 1
                return
        raise KeyError(f"Автомобіль з ID {car_id} не знайдено")

    def remove(self, car_id: int) -> None:
        """Remove a car and invalidate the cache."""
        before = len(self._cars)
        self._cars = [car for car in self._cars if car.car_id != car_id]
        if len(self._cars) == before:
            raise KeyError(f"Автомобіль з ID {car_id} не знайдено")
        self.version += 1

    def brand_statistics(self, brand: str) -> BrandStatistics:
        """Statistics of a brand from the cache (" toyota" and "Toyota" are one key)."""
        return _cached_brand_statistics(self, brand.strip().lower(), self.version)

    def manufacturer_statistics(self) -> dict[str, BrandStatistics]:
        """Statistics of all manufacturers from the cache."""
        return _cached_manufacturer_statistics(self, self.version)


@lru_cache(maxsize=128)
def _cached_brand_statistics(
    catalog: CachedCarCatalog, brand: str, version: int
) -> BrandStatistics:
    """Calculated only on a cache miss; `version` is used only as a part of the key."""
    return brand_statistics(catalog.cars, brand)


@lru_cache(maxsize=16)
def _cached_manufacturer_statistics(
    catalog: CachedCarCatalog, version: int
) -> dict[str, BrandStatistics]:
    """Calculated only on a cache miss."""
    return manufacturer_statistics(catalog.cars)


def brand_cache_info() -> tuple[int, int, int]:
    """(hits, misses, currsize) of the brand statistics cache."""
    info = _cached_brand_statistics.cache_info()
    return info.hits, info.misses, info.currsize


def clear_caches() -> None:
    """Empty both caches (cache_clear)."""
    _cached_brand_statistics.cache_clear()
    _cached_manufacturer_statistics.cache_clear()
