"""Business logic of the car catalog."""

from car_catalog.models import Car


class EmptyCatalogError(ValueError):
    """Raised when a calculation needs at least one car in the catalog."""


def add_car(cars: list[Car], car: Car) -> None:
    """Add a car to the catalog."""
    cars.append(car)


def find_cars_by_brand(cars: list[Car], brand: str) -> list[Car]:
    """Return cars of the given brand (case-insensitive)."""
    return [car for car in cars if car.brand.lower() == brand.strip().lower()]


def filter_cars_by_year(
    cars: list[Car], min_year: int, max_year: int | None = None
) -> list[Car]:
    """Return cars made in the year range from min_year to max_year."""
    result = []
    for car in cars:
        if car.year < min_year:
            continue
        if max_year is not None and car.year > max_year:
            continue
        result.append(car)
    return result


def search_cars(
    cars: list[Car],
    brand: str = "",
    min_year: int | None = None,
    max_price: float | None = None,
) -> list[Car]:
    """Return cars matching a brand, a minimum year and a maximum price."""
    result = cars
    if brand.strip():
        result = find_cars_by_brand(result, brand)
    if min_year is not None:
        result = filter_cars_by_year(result, min_year)
    if max_price is not None:
        result = [car for car in result if car.price <= max_price]
    return result


def find_most_expensive_car(cars: list[Car]) -> Car | None:
    """Return the most expensive car or None for an empty catalog."""
    return max(cars, key=lambda car: car.price, default=None)


def calculate_average_price(cars: list[Car]) -> float:
    """Return the average price of cars in the catalog."""
    if not cars:
        raise EmptyCatalogError("Каталог порожній: середню ціну обчислити неможливо.")
    return sum(car.price for car in cars) / len(cars)


def find_lowest_mileage_car(cars: list[Car]) -> Car | None:
    """Return the car with the lowest mileage or None for an empty catalog."""
    return min(cars, key=lambda car: car.mileage, default=None)


def sort_cars_by_price(cars: list[Car], descending: bool = False) -> list[Car]:
    """Return cars sorted by price."""
    return sorted(cars, key=lambda car: car.price, reverse=descending)
