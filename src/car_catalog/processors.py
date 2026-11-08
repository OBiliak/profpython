"""Processing of car records: unique values, index, filtering and grouping."""

from collections import Counter, defaultdict

from car_catalog.decorators import log_operation


def get_unique_brands(cars: list[dict]) -> set[str]:
    """Return the set of unique car brands."""
    return {car["brand"] for car in cars}


def create_car_index(cars: list[dict]) -> dict[int, dict]:
    """Return a dict index of cars by ID."""
    return {car["id"]: car for car in cars}


def find_car_by_id(index: dict[int, dict], car_id: int) -> dict | None:
    """Return a car from the index by ID or None."""
    return index.get(car_id)


def find_car_linear(cars: list[dict], car_id: int) -> dict | None:
    """Return a car by ID using linear search in the list or None."""
    for car in cars:
        if car["id"] == car_id:
            return car
    return None


@log_operation("фільтр за роком")
def filter_by_year(cars: list[dict], min_year: int, max_year: int | None = None) -> list[dict]:
    """Return cars made from min_year to max_year inclusive."""
    return [
        car
        for car in cars
        if car["year"] >= min_year and (max_year is None or car["year"] <= max_year)
    ]


def group_by_brand(cars: list[dict]) -> dict[str, list[dict]]:
    """Return cars grouped by brand."""
    result = defaultdict(list)
    for car in cars:
        result[car["brand"]].append(car)
    return dict(result)


def group_by_brand_and_year(cars: list[dict]) -> dict[str, dict[int, list[str]]]:
    """Return car models grouped by brand and then by year."""
    result: defaultdict[str, defaultdict[int, list[str]]] = defaultdict(lambda: defaultdict(list))
    for car in cars:
        result[car["brand"]][car["year"]].append(car["model"])
    return {brand: dict(years) for brand, years in result.items()}


def count_cars_by_brand(cars: list[dict]) -> Counter:
    """Return the number of cars of each brand."""
    return Counter(car["brand"] for car in cars)
