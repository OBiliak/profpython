"""Streaming aggregation and search over car records."""

from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from itertools import accumulate, groupby, islice

from car_catalog.stream.models import CarRecord


def calculate_statistics(cars: Iterable[CarRecord]) -> dict:
    """Return count, average price, most expensive and lowest mileage car in one pass."""
    count = 0
    total = 0.0
    most_expensive = None
    lowest_mileage = None
    brands = Counter()
    for car in cars:
        count += 1
        total += car.price
        brands[car.brand] += 1
        if most_expensive is None or car.price > most_expensive.price:
            most_expensive = car
        if lowest_mileage is None or car.mileage < lowest_mileage.mileage:
            lowest_mileage = car
    return {
        "count": count,
        "average_price": total / count if count else 0.0,
        "most_expensive": most_expensive,
        "lowest_mileage": lowest_mileage,
        "brands": brands,
    }


def running_average_prices(cars: Iterable[CarRecord]) -> Iterator[float]:
    """Yield the average price after each car of the stream."""
    prices = (car.price for car in cars)
    for number, total in enumerate(accumulate(prices), start=1):
        yield total / number


def find_first(
    cars: Iterable[CarRecord], predicate: Callable[[CarRecord], bool]
) -> CarRecord | None:
    """Return the first car matching the predicate and stop reading the stream."""
    for car in cars:
        if predicate(car):
            return car
    return None


def take_first_n(
    cars: Iterable[CarRecord], predicate: Callable[[CarRecord], bool], n: int
) -> list[CarRecord]:
    """Return the first n cars matching the predicate."""
    return list(islice((car for car in cars if predicate(car)), n))


def count_by_brand_sorted(cars: Iterable[CarRecord]) -> dict[str, int]:
    """Return the number of cars of each brand using groupby after sorting."""
    sorted_cars = sorted(cars, key=lambda car: car.brand)
    return {
        brand: sum(1 for _ in group)
        for brand, group in groupby(sorted_cars, key=lambda car: car.brand)
    }
