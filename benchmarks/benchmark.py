"""Benchmarks of laboratory work 9: python benchmarks/benchmark.py (from the project root).

Experiments (5 repeats each, perf_counter):
  residual  — CPU-bound residual values: Sequential, Threads, Processes (1/2/4/8), NumPy;
  analytics — functions of laboratory work 1 and statistics: Python loops vs NumPy;
  files     — I/O-bound reading of 8 compressed catalog files: sequential vs threads;
  cache     — repeated brand statistics: without cache, cache hit, miss after a change.
Results: benchmarks/results/benchmark_results.csv and PNG charts (plot_results.py).
"""

from __future__ import annotations

import argparse
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from car_catalog.performance import analytics, vectorized
from car_catalog.performance.analytics import CarRecord, generate_cars
from car_catalog.performance.benchmarking import (
    BenchmarkResult,
    add_speedups,
    benchmark_repeated,
    save_csv,
)
from car_catalog.performance.caching import CachedCarCatalog, clear_caches
from car_catalog.performance.parallel import (
    load_parts_sequential,
    load_parts_threads,
    read_parts_sequential,
    read_parts_threads,
    read_parts_with_threading,
    residual_values_processes,
    residual_values_threads,
    write_catalog_parts,
)
from car_catalog.performance.profiling import measure_memory

RESULTS = Path(__file__).parent / "results"
SIZES = [10_000, 100_000, 250_000]
WORKERS = [1, 2, 4, 8]


def python_statistics(cars: list[CarRecord]) -> tuple[object, ...]:
    """Functions of laboratory work 1 and statistics with Python loops."""
    return (
        len(analytics.find_by_brand(cars, "Toyota")),
        len(analytics.filter_by_year(cars, 2019, 2022)),
        analytics.most_expensive(cars).car_id,
        analytics.lowest_mileage(cars).car_id,
        analytics.average_price(cars),
        analytics.mileage_statistics(cars),
        analytics.manufacturer_statistics(cars),
    )


def numpy_statistics(arrays: vectorized.CatalogArrays) -> tuple[object, ...]:
    """The same with NumPy arrays."""
    return (
        vectorized.count_by_brand(arrays, "Toyota"),
        vectorized.count_by_years(arrays, 2019, 2022),
        vectorized.most_expensive_id(arrays),
        vectorized.lowest_mileage_id(arrays),
        vectorized.average_price(arrays),
        vectorized.mileage_statistics(arrays),
        vectorized.manufacturer_statistics(arrays),
    )


def run(
    results: list[BenchmarkResult],
    experiment: str,
    method: str,
    size: int,
    workers: int | None,
    repeats: int,
    memory: bool,
    function: Callable[..., Any],
    *args: Any,
) -> Any:
    """Measure one method, add the result to the list and print a line."""
    times, value = benchmark_repeated(function, *args, repeats=repeats)
    item = BenchmarkResult(experiment, method, size, workers, times)
    if memory:  # a separate run: tracemalloc slows the program down
        _, _, item.peak_memory_mb = measure_memory(function, *args)
    results.append(item)
    print(f"{experiment:9} {method:22} {size:>7} {workers or '-':>2}  mean {item.mean:.4f} s")
    return value


def residual_experiment(
    results: list[BenchmarkResult], cars: list[CarRecord], repeats: int, memory: bool
) -> None:
    """CPU-bound residual values; every optimized result is compared with the baseline."""
    size = len(cars)
    expected = run(
        results,
        "residual",
        "Sequential",
        size,
        None,
        repeats,
        memory,
        analytics.residual_values_sequential,
        cars,
    )
    for workers in WORKERS:
        value = run(
            results,
            "residual",
            "Threads",
            size,
            workers,
            repeats,
            memory,
            residual_values_threads,
            cars,
            workers,
        )
        assert value == expected
    for workers in WORKERS:
        value = run(
            results,
            "residual",
            "Processes",
            size,
            workers,
            repeats,
            memory,
            residual_values_processes,
            cars,
            workers,
        )
        assert value == expected
    arrays = vectorized.to_arrays(cars)
    value = run(
        results,
        "residual",
        "NumPy",
        size,
        None,
        repeats,
        memory,
        vectorized.residual_values,
        arrays,
    )
    assert np.allclose(value, expected, rtol=1e-9)
    run(
        results,
        "residual",
        "NumPy + to_arrays",
        size,
        None,
        repeats,
        memory,
        lambda: vectorized.residual_values(vectorized.to_arrays(cars)),
    )


def analytics_experiment(
    results: list[BenchmarkResult], cars: list[CarRecord], repeats: int, memory: bool
) -> None:
    """Statistics of the catalog: Python loops vs NumPy."""
    size = len(cars)
    expected = run(
        results, "analytics", "Python loops", size, None, repeats, memory, python_statistics, cars
    )
    arrays = vectorized.to_arrays(cars)
    value = run(
        results, "analytics", "NumPy", size, None, repeats, memory, numpy_statistics, arrays
    )
    assert value[:4] == expected[:4]


def files_experiment(
    results: list[BenchmarkResult], cars: list[CarRecord], repeats: int, memory: bool
) -> None:
    """I/O-bound: 8 compressed files; reading in threads and full loading with parsing."""
    size = len(cars)
    with tempfile.TemporaryDirectory() as directory:
        paths = write_catalog_parts(cars, Path(directory), parts=8)
        expected = run(
            results,
            "files_read",
            "Sequential",
            size,
            None,
            repeats,
            memory,
            read_parts_sequential,
            paths,
        )
        for workers in (2, 4, 8):
            value = run(
                results,
                "files_read",
                "ThreadPoolExecutor",
                size,
                workers,
                repeats,
                memory,
                read_parts_threads,
                paths,
                workers,
            )
            assert value == expected
        value = run(
            results,
            "files_read",
            "threading.Thread",
            size,
            len(paths),
            repeats,
            memory,
            read_parts_with_threading,
            paths,
        )
        assert value == expected
        loaded = run(
            results,
            "files_load",
            "Sequential",
            size,
            None,
            repeats,
            memory,
            load_parts_sequential,
            paths,
        )
        assert loaded == cars
        loaded = run(
            results,
            "files_load",
            "ThreadPoolExecutor",
            size,
            8,
            repeats,
            memory,
            load_parts_threads,
            paths,
            8,
        )
        assert loaded == cars


CALLS = 100  # one cached call takes about a microsecond, so a run is 100 repeated requests


def cache_experiment(results: list[BenchmarkResult], cars: list[CarRecord], repeats: int) -> None:
    """100 requests of Toyota statistics: without cache / cache hits / every request after a change."""
    size = len(cars)
    clear_caches()
    catalog = CachedCarCatalog(cars)

    def without_cache() -> object:
        return [analytics.brand_statistics(catalog.cars, "Toyota") for _ in range(CALLS)][-1]

    def with_cache() -> object:
        return [catalog.brand_statistics("Toyota") for _ in range(CALLS)][-1]

    def change_then_read() -> object:
        for _ in range(CALLS):
            catalog.update_price(1, catalog.cars[0].price + 1)  # invalidation: version + 1
            statistics = catalog.brand_statistics("Toyota")
        return statistics

    expected = run(results, "cache", "No cache", size, None, repeats, False, without_cache)
    catalog.brand_statistics("Toyota")  # the first call is a miss and fills the cache
    value = run(results, "cache", "lru_cache (hit)", size, None, repeats, False, with_cache)
    assert value == expected
    run(results, "cache", "Change + miss", size, None, repeats, False, change_then_read)


def main() -> None:
    parser = argparse.ArgumentParser(description="Бенчмарки ЛР9")
    parser.add_argument("--sizes", type=int, nargs="+", default=SIZES)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--output", type=Path, default=RESULTS / "benchmark_results.csv")
    args = parser.parse_args()

    results: list[BenchmarkResult] = []
    largest = max(args.sizes)
    for size in args.sizes:
        cars = generate_cars(size)
        memory = size == largest  # peak memory only for the largest set
        residual_experiment(results, cars, args.repeats, memory)
        analytics_experiment(results, cars, args.repeats, memory)
    cars = generate_cars(largest)
    files_experiment(results, cars, args.repeats, True)
    cache_experiment(results, cars, args.repeats)

    add_speedups(results, "Sequential")
    add_speedups([item for item in results if item.experiment == "analytics"], "Python loops")
    add_speedups([item for item in results if item.experiment == "cache"], "No cache")
    save_csv(results, args.output)
    print(f"Результати збережено: {args.output}")


if __name__ == "__main__":
    main()
