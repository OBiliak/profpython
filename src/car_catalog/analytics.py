"""Analytics of the car catalog: statistics, sorting and filters."""

from collections.abc import Callable

from car_catalog.decorators import log_operation, measure_time


@measure_time
def calculate_average_price(cars: list[dict]) -> float:
    """Return the average car price or 0.0 for an empty catalog."""
    if not cars:
        return 0.0
    return sum(car["price"] for car in cars) / len(cars)


def find_most_expensive_car(cars: list[dict]) -> dict | None:
    """Return the most expensive car or None."""
    return max(cars, key=lambda car: car["price"], default=None)


def find_lowest_mileage_car(cars: list[dict]) -> dict | None:
    """Return the car with the lowest mileage or None."""
    return min(cars, key=lambda car: car["mileage"], default=None)


@log_operation("сортування за ціною")
def sort_by_price(cars: list[dict], reverse: bool = False) -> list[dict]:
    """Return cars sorted by price."""
    return sorted(cars, key=lambda car: car["price"], reverse=reverse)


def sort_cars(cars: list[dict], field: str, reverse: bool = False) -> list[dict]:
    """Return cars sorted by any field of the record."""
    return sorted(cars, key=lambda car: car[field], reverse=reverse)


def calculate_average_values(*values: float) -> float:
    """Return the average of any number of values or 0.0."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def create_car_record(**fields) -> dict:
    """Return a new car record built from keyword arguments."""
    return dict(fields)


def create_price_filter(max_price: float) -> Callable[[dict], bool]:
    """Return a predicate that accepts cars not more expensive than max_price."""

    def predicate(car: dict) -> bool:
        return car["price"] <= max_price

    return predicate


def create_mileage_filter(max_mileage: int) -> Callable[[dict], bool]:
    """Return a predicate that accepts cars with mileage up to max_mileage."""

    def predicate(car: dict) -> bool:
        return car["mileage"] <= max_mileage

    return predicate


@log_operation("універсальний фільтр")
def filter_cars(cars: list[dict], *predicates: Callable[[dict], bool]) -> list[dict]:
    """Return cars that satisfy all given predicates."""
    return [car for car in cars if all(predicate(car) for predicate in predicates)]
