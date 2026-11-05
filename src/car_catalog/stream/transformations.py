"""Transformation stage: normalization of car records."""

from collections.abc import Iterable, Iterator

from car_catalog.stream.models import CarRecord


def normalize_brand(brand: str) -> str:
    """Return a brand with a capital first letter, keeping abbreviations like BMW."""
    return brand if brand.isupper() else brand.title()


def normalize_cars(cars: Iterable[CarRecord]) -> Iterator[CarRecord]:
    """Yield cars with normalized brand names."""
    for car in cars:
        yield car._replace(brand=normalize_brand(car.brand))
