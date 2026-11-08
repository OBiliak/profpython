"""Experiment: eager vs lazy processing (time, peak memory, time to first result)."""

import csv
import tracemalloc
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from time import perf_counter

from car_catalog.stream.analytics import calculate_statistics, find_first
from car_catalog.stream.filters import parse_car
from car_catalog.stream.generate import ensure_dataset
from car_catalog.stream.models import CarRecord
from car_catalog.stream.parsers import HEADER
from car_catalog.stream.pipeline import build_pipeline
from car_catalog.stream.transformations import normalize_brand

SIZES = (10_000, 100_000, 500_000)
EARLY_TERMINATION_SIZE = 1_000_000
MIN_YEAR = 2015
REPEATS = 3


def build_eager(path: Path) -> list[CarRecord]:
    """Return all filtered and normalized cars, building a full list at every stage."""
    with path.open(encoding="utf-8") as file:
        lines = file.readlines()
    cleaned = [line.strip() for line in lines if line.strip()]
    rows = [row for row in csv.reader(cleaned) if row != HEADER]
    cars = []
    for row in rows:
        try:
            cars.append(parse_car(row))
        except ValueError:
            continue
    filtered = [car for car in cars if car.year >= MIN_YEAR]
    return [car._replace(brand=normalize_brand(car.brand)) for car in filtered]


def run_eager(path: Path) -> dict:
    """Return statistics computed from fully materialized lists."""
    return calculate_statistics(build_eager(path))


def run_lazy(path: Path) -> dict:
    """Return statistics computed from the lazy pipeline."""
    return calculate_statistics(build_pipeline([path], Counter(), min_year=MIN_YEAR))


def measure_time(func: Callable[[], object]) -> float:
    """Return the best elapsed time of func in seconds over REPEATS runs."""
    times = []
    for _ in range(REPEATS):
        start = perf_counter()
        func()
        times.append(perf_counter() - start)
    return min(times)


def measure_peak_memory(func: Callable[[], object]) -> float:
    """Return the peak memory used by func in MB."""
    tracemalloc.start()
    func()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak / 1024 / 1024


def compare(path: Path) -> tuple[float, float, float, float, float, float, bool]:
    """Return times, peak memory, times to first result and whether results are equal."""
    eager_time = measure_time(lambda: run_eager(path))
    lazy_time = measure_time(lambda: run_lazy(path))
    eager_memory = measure_peak_memory(lambda: run_eager(path))
    lazy_memory = measure_peak_memory(lambda: run_lazy(path))
    eager_first = measure_time(lambda: build_eager(path)[0])
    lazy_first = measure_time(lambda: next(build_pipeline([path], Counter(), min_year=MIN_YEAR)))
    same = run_eager(path) == run_lazy(path)
    return eager_time, lazy_time, eager_memory, lazy_memory, eager_first, lazy_first, same


def print_comparison() -> None:
    """Print the eager vs lazy table for all dataset sizes."""
    print(f"Eager vs lazy: валідація, фільтр year >= {MIN_YEAR}, нормалізація, статистика")
    print(f"(час — найкращий з {REPEATS} запусків; пам'ять — tracemalloc peak)\n")
    print(
        f"{'Records':>8} | {'Eager, с':>8} | {'Lazy, с':>8} | {'Eager, МБ':>9} | "
        f"{'Lazy, МБ':>8} | {'TTFR eager, мс':>14} | {'TTFR lazy, мс':>13} | Рівні"
    )
    print("-" * 98)
    for size in SIZES:
        result = compare(ensure_dataset(size))
        eager_time, lazy_time, eager_memory, lazy_memory, eager_first, lazy_first, same = result
        print(
            f"{size:>8} | {eager_time:>8.3f} | {lazy_time:>8.3f} | {eager_memory:>9.2f} | "
            f"{lazy_memory:>8.3f} | {eager_first * 1000:>14.1f} | {lazy_first * 1000:>13.3f} | {same}"
        )


def print_early_termination() -> None:
    """Print the early termination experiment on a large dataset."""
    path = ensure_dataset(EARLY_TERMINATION_SIZE)

    def predicate(car: CarRecord) -> bool:
        return car.brand == "BMW" and car.year == 2026 and car.mileage == 0

    print(
        f"\nEarly termination: {EARLY_TERMINATION_SIZE} записів, перший BMW 2026 року з пробігом 0"
    )
    lazy_time = measure_time(lambda: find_first(build_pipeline([path], Counter()), predicate))
    eager_time = measure_time(lambda: [car for car in build_eager(path) if predicate(car)][0])
    lazy_memory = measure_peak_memory(
        lambda: find_first(build_pipeline([path], Counter()), predicate)
    )
    eager_memory = measure_peak_memory(
        lambda: [car for car in build_eager(path) if predicate(car)][0]
    )
    found = find_first(build_pipeline([path], Counter()), predicate)
    print(f"Знайдено: {found}")
    print(f"Lazy find_first:       {lazy_time:.4f} с, peak {lazy_memory:.3f} МБ")
    print(f"Eager filtered list:   {eager_time:.4f} с, peak {eager_memory:.2f} МБ")
    print(f"Lazy швидший у {eager_time / lazy_time:.0f} разів")


def main() -> None:
    """Run both experiments."""
    print_comparison()
    print_early_termination()


if __name__ == "__main__":
    main()
