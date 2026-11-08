"""Test data and the baseline (pure Python) analytics of the car catalog."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

BRAND_MODELS: dict[str, tuple[str, ...]] = {
    "Toyota": ("Corolla", "RAV4", "Camry", "Prius", "Land Cruiser"),
    "Volkswagen": ("Golf", "Passat", "Tiguan", "Polo"),
    "Skoda": ("Octavia", "Fabia", "Kodiaq", "Superb"),
    "BMW": ("X5", "320i", "X3", "530d"),
    "Renault": ("Logan", "Duster", "Megane", "Clio"),
    "Mercedes-Benz": ("C-Class", "E-Class", "GLC", "S-Class"),
    "Audi": ("A4", "A6", "Q5", "Q7"),
    "Hyundai": ("Tucson", "Elantra", "Santa Fe", "i30"),
    "Nissan": ("Leaf", "Qashqai", "X-Trail", "Juke"),
    "Tesla": ("Model 3", "Model Y", "Model S", "Model X"),
}
BRANDS = tuple(BRAND_MODELS)
MONTHS = 120  # residual value is modelled for 10 years, month by month
CURRENT_YEAR = 2026


@dataclass(frozen=True, slots=True)
class CarRecord:
    """One car of the large test catalog."""

    car_id: int
    brand: str
    model: str
    year: int
    price: float
    mileage: int


@dataclass(frozen=True)
class MileageStatistics:
    """Minimum, maximum, average and standard deviation of mileage."""

    minimum: int
    maximum: int
    average: float
    std: float


@dataclass(frozen=True)
class BrandStatistics:
    """Statistics of one manufacturer (brand)."""

    count: int
    average_price: float
    average_mileage: float
    max_price: float


def generate_cars(count: int, seed: int = 42) -> list[CarRecord]:
    """Create `count` cars with fixed random data (the same seed gives the same catalog)."""
    generator = random.Random(seed)
    cars = []
    for car_id in range(1, count + 1):
        brand = generator.choice(BRANDS)
        year = generator.randint(1995, CURRENT_YEAR)
        age = CURRENT_YEAR - year
        cars.append(
            CarRecord(
                car_id=car_id,
                brand=brand,
                model=generator.choice(BRAND_MODELS[brand]),
                year=year,
                price=round(generator.uniform(150_000, 4_500_000), 2),
                mileage=generator.randint(0, 20_000 + age * 18_000),
            )
        )
    return cars


# --- Functions of laboratory work 1 on the large catalog (baseline: loops over Python objects) ---


def find_by_brand(cars: list[CarRecord], brand: str) -> list[CarRecord]:
    """Search by brand (case-insensitive)."""
    wanted = brand.strip().lower()
    return [car for car in cars if car.brand.lower() == wanted]


def filter_by_year(cars: list[CarRecord], min_year: int, max_year: int) -> list[CarRecord]:
    """Cars with min_year <= year <= max_year."""
    return [car for car in cars if min_year <= car.year <= max_year]


def most_expensive(cars: list[CarRecord]) -> CarRecord:
    """The most expensive car."""
    best = cars[0]
    for car in cars:
        if car.price > best.price:
            best = car
    return best


def lowest_mileage(cars: list[CarRecord]) -> CarRecord:
    """The car with the lowest mileage."""
    best = cars[0]
    for car in cars:
        if car.mileage < best.mileage:
            best = car
    return best


def average_price(cars: list[CarRecord]) -> float:
    """Average price (loop, as the baseline)."""
    total = 0.0
    for car in cars:
        total += car.price
    return total / len(cars)


def mileage_statistics(cars: list[CarRecord]) -> MileageStatistics:
    """Min, max, average and standard deviation of mileage."""
    values = [car.mileage for car in cars]
    average = sum(values) / len(values)
    variance = sum((value - average) ** 2 for value in values) / len(values)
    return MileageStatistics(min(values), max(values), average, math.sqrt(variance))


def brand_statistics(cars: list[CarRecord], brand: str) -> BrandStatistics:
    """Statistics of one brand: count, average price, average mileage, max price."""
    selected = find_by_brand(cars, brand)
    if not selected:
        return BrandStatistics(0, 0.0, 0.0, 0.0)
    prices = [car.price for car in selected]
    return BrandStatistics(
        count=len(selected),
        average_price=sum(prices) / len(prices),
        average_mileage=sum(car.mileage for car in selected) / len(selected),
        max_price=max(prices),
    )


def manufacturer_statistics(cars: list[CarRecord]) -> dict[str, BrandStatistics]:
    """Statistics of every manufacturer in one pass over the catalog."""
    totals: dict[str, list[float]] = {}
    for car in cars:
        item = totals.setdefault(car.brand, [0, 0.0, 0.0, 0.0])
        item[0] += 1
        item[1] += car.price
        item[2] += car.mileage
        item[3] = max(item[3], car.price)
    return {
        brand: BrandStatistics(int(count), price_sum / count, mileage_sum / count, max_price)
        for brand, (count, price_sum, mileage_sum, max_price) in sorted(totals.items())
    }


# --- CPU-bound analytics: residual value of every car after 10 years ---


def residual_value(price: float, year: int, mileage: int) -> float:
    """Residual value after MONTHS months: monthly depreciation depends on age and mileage.

    Every month the car loses 0.5–1.5 % of its value (a seasonal sin² term) and an amount
    for wear that grows with the mileage. The loop of 120 steps makes the task CPU-bound.
    """
    value = price
    age = CURRENT_YEAR - year
    for month in range(1, MONTHS + 1):
        rate = 0.005 + 0.01 * math.sin((month + age) / 6) ** 2
        wear = mileage * 0.0004 * math.sqrt(month) / MONTHS
        value = value * (1 - rate) - wear
    return max(value, 0.0)


def car_residual_value(car: CarRecord) -> float:
    """residual_value() of one car (a function of one argument for executor.map)."""
    return residual_value(car.price, car.year, car.mileage)


def residual_values_sequential(cars: list[CarRecord]) -> list[float]:
    """Baseline: residual values of all cars one after another."""
    return [car_residual_value(car) for car in cars]


def catalog_report(cars: list[CarRecord]) -> dict[str, object]:
    """Everything the catalog shows: functions of laboratory work 1, statistics and residual values."""
    residuals = residual_values_sequential(cars)
    return {
        "toyota": len(find_by_brand(cars, "Toyota")),
        "years_2019_2022": len(filter_by_year(cars, 2019, 2022)),
        "most_expensive": most_expensive(cars),
        "lowest_mileage": lowest_mileage(cars),
        "average_price": average_price(cars),
        "mileage": mileage_statistics(cars),
        "manufacturers": manufacturer_statistics(cars),
        "average_residual": sum(residuals) / len(residuals),
    }
