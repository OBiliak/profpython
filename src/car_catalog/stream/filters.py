"""Validation and filtering stages of the pipeline."""

from collections import Counter
from collections.abc import Iterable, Iterator

from car_catalog.config import MAX_YEAR, MIN_YEAR
from car_catalog.stream.models import CarRecord


def parse_car(row: list[str]) -> CarRecord:
    """Convert a CSV row to CarRecord or raise ValueError for invalid data."""
    if len(row) != 6:
        raise ValueError(f"очікується 6 полів, отримано {len(row)}")
    car = CarRecord(
        id=int(row[0]),
        brand=row[1].strip(),
        model=row[2].strip(),
        year=int(row[3]),
        price=float(row[4]),
        mileage=int(row[5]),
    )
    if car.id <= 0 or not car.brand or not car.model:
        raise ValueError("некоректний id, марка або модель")
    if not MIN_YEAR <= car.year <= MAX_YEAR:
        raise ValueError(f"рік {car.year} поза межами {MIN_YEAR}–{MAX_YEAR}")
    if car.price <= 0 or car.mileage < 0:
        raise ValueError("ціна має бути > 0, пробіг >= 0")
    return car


def validate_cars(rows: Iterable[list[str]], stats: Counter) -> Iterator[CarRecord]:
    """Yield valid cars and count valid and invalid rows in stats."""
    for row in rows:
        try:
            car = parse_car(row)
        except ValueError:
            stats["invalid"] += 1
            continue
        stats["valid"] += 1
        yield car


def filter_by_brand(cars: Iterable[CarRecord], brands: set[str]) -> Iterator[CarRecord]:
    """Yield cars of the given brands (case-insensitive)."""
    wanted = {brand.lower() for brand in brands}
    for car in cars:
        if car.brand.lower() in wanted:
            yield car


def filter_by_year(
    cars: Iterable[CarRecord], min_year: int, max_year: int = MAX_YEAR
) -> Iterator[CarRecord]:
    """Yield cars made from min_year to max_year inclusive."""
    for car in cars:
        if min_year <= car.year <= max_year:
            yield car
