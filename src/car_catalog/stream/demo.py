"""Streaming processing demo of the car catalog (laboratory work 3)."""

from collections import Counter
from collections.abc import Iterable
from itertools import islice
from pathlib import Path
from time import perf_counter

from car_catalog.config import CURRENCY
from car_catalog.stream.analytics import (
    calculate_statistics,
    count_by_brand_sorted,
    find_first,
    running_average_prices,
    take_first_n,
)
from car_catalog.stream.batches import batched_cars
from car_catalog.stream.generate import ensure_dataset
from car_catalog.stream.iterators import CarIdRange, generate_ids
from car_catalog.stream.models import CarRecord
from car_catalog.stream.pipeline import build_pipeline

DEMO_FILES = (Path("data/cars.csv"), Path("data/cars_extra.csv"))
LARGE_DATASET_SIZE = 100_000


def format_car(car: CarRecord | None) -> str:
    """Return one line with all fields of a car or a message for None."""
    if car is None:
        return "автомобіль не знайдено"
    return (
        f"{car.id:>6}  {car.brand:<11} {car.model:<12} {car.year}  "
        f"{car.price:>11.2f} {CURRENCY}  {car.mileage:>7} км"
    )


def print_cars(title: str, cars: list[CarRecord]) -> None:
    """Print a title and a table of cars."""
    print(f"\n{title}")
    for car in cars:
        print(format_car(car))


def show_iterator_protocol() -> None:
    """Show iter(), next(), StopIteration, a custom iterator and an infinite generator."""
    print("\n--- Iterator protocol ---")
    ids = CarIdRange(1, 3)
    print(f"iter(ids) is ids: {iter(ids) is ids}")
    print(f"next(ids): {next(ids)}, {next(ids)}, {next(ids)}")
    try:
        next(ids)
    except StopIteration:
        print("next(ids) після останнього ID -> StopIteration")
    print(f"Повторний прохід вичерпаного iterator: {list(ids)}")
    print(f"islice(generate_ids(1000), 5): {list(islice(generate_ids(1000), 5))}")


def show_statistics(title: str, cars: Iterable[CarRecord]) -> None:
    """Print streaming statistics of cars."""
    stats = calculate_statistics(cars)
    print(f"\n{title}")
    print(f"Кількість: {stats['count']}")
    print(f"Середня ціна: {stats['average_price']:.2f} {CURRENCY}")
    print(f"Найдорожчий: {format_car(stats['most_expensive'])}")
    print(f"Найменший пробіг: {format_car(stats['lowest_mileage'])}")


def show_demo_files() -> None:
    """Run the pipeline on two small demo CSV files joined by chain."""
    print("\n--- Демонстраційні файли: data/cars.csv + data/cars_extra.csv ---")
    stats: Counter[str] = Counter()
    first_cars = list(islice(build_pipeline(DEMO_FILES, stats), 5))
    print_cars("Перші 5 валідних записів (islice):", first_cars)

    stats = Counter()
    show_statistics("Статистика за один прохід:", build_pipeline(DEMO_FILES, stats))
    print(f"Валідних записів: {stats['valid']}, невалідних: {stats['invalid']}")

    toyota = build_pipeline(DEMO_FILES, Counter(), brands={"toyota"}, min_year=2018)
    print_cars("Фільтр: марка Toyota, рік від 2018:", list(toyota))

    averages = running_average_prices(build_pipeline(DEMO_FILES, Counter()))
    first_averages = [f"{value:.2f}" for value in islice(averages, 5)]
    print(f"\nStreaming average price (перші 5 кроків): {first_averages}")

    cars = build_pipeline(DEMO_FILES, Counter())
    cheap = take_first_n(cars, lambda car: car.price < 500_000, 3)
    print_cars("Перші 3 автомобілі з ціною до 500000 грн:", cheap)

    print("\nBatching по 4 записи:")
    batches = batched_cars(build_pipeline(DEMO_FILES, Counter()), 4)
    for number, batch in enumerate(batches, start=1):
        print(f"  batch {number}: розмір {len(batch)}, ID {[car.id for car in batch]}")

    groups = count_by_brand_sorted(build_pipeline(DEMO_FILES, Counter()))
    print(f"\ngroupby за маркою після сортування: {groups}")


def show_large_dataset() -> None:
    """Run the pipeline on a generated dataset with LARGE_DATASET_SIZE records."""
    path = ensure_dataset(LARGE_DATASET_SIZE)
    print(f"\n--- Великий набір: {path} ({LARGE_DATASET_SIZE} записів) ---")
    start = perf_counter()
    first = next(build_pipeline([path], Counter()))
    print(f"Time to first result: {(perf_counter() - start) * 1000:.3f} мс -> {format_car(first)}")

    stats: Counter[str] = Counter()
    start = perf_counter()
    show_statistics("Статистика за один прохід:", build_pipeline([path], stats))
    print(f"Валідних записів: {stats['valid']}, невалідних: {stats['invalid']}")
    print(f"Час повного проходу: {perf_counter() - start:.3f} с")

    batches = batched_cars(build_pipeline([path], Counter()), 10_000)
    print(f"Batching по 10000: {[len(batch) for batch in batches]}")

    cars = build_pipeline([path], Counter())
    found = find_first(cars, lambda car: car.price > 2_400_000 and car.year == 2026)
    print(f"Перший автомобіль 2026 року дорожчий за 2400000 грн: {format_car(found)}")
    print(f"groupby за маркою: {count_by_brand_sorted(build_pipeline([path], Counter()))}")


def main() -> None:
    """Run the streaming demonstration of laboratory work 3."""
    print("=== Потокова обробка каталогу автомобілів (лабораторна робота №3, варіант 5) ===")
    show_iterator_protocol()
    show_demo_files()
    show_large_dataset()


if __name__ == "__main__":
    main()
