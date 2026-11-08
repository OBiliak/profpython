"""Performance demo of laboratory work 9: python -m car_catalog.main [number of cars].

Profiling of the large catalog (cProfile, tracemalloc, timeit), then the optimizations of the
bottleneck: threads, processes, NumPy, Lock for shared state and lru_cache with invalidation.
The full experiment with 5 repeats and charts: python benchmarks/benchmark.py.
The REST API demo of laboratory work 8: python -m car_catalog.api_demo.
"""

import os
import sys
import tempfile
from pathlib import Path

import numpy as np

from car_catalog.performance import analytics, vectorized
from car_catalog.performance.analytics import CarRecord, generate_cars
from car_catalog.performance.benchmarking import calculate_speedup, measure
from car_catalog.performance.caching import CachedCarCatalog, brand_cache_info, clear_caches
from car_catalog.performance.parallel import (
    count_in_threads,
    load_parts_sequential,
    load_parts_threads,
    read_parts_sequential,
    read_parts_threads,
    read_parts_with_threading,
    residual_sum_with_processes,
    residual_values_processes,
    residual_values_threads,
    write_catalog_parts,
)
from car_catalog.performance.profiling import measure_memory, profile_call, time_with_timeit

DEFAULT_COUNT = 250_000
WORKERS = 4


def title(text: str) -> None:
    """Heading of a demo part."""
    print(f"\n=== {text} ===")


def show_baseline(cars: list[CarRecord]) -> None:
    """Functions of laboratory work 1 and the full report with Python loops."""
    title("1. Baseline: звіт каталогу на циклах Python")
    elapsed, report = measure(analytics.catalog_report, cars)
    expensive = report["most_expensive"]
    cheapest_mileage = report["lowest_mileage"]
    assert isinstance(expensive, CarRecord) and isinstance(cheapest_mileage, CarRecord)
    print(f"Toyota: {report['toyota']} авто; роки 2019–2022: {report['years_2019_2022']} авто")
    print(
        f"Найдорожчий: {expensive.brand} {expensive.model} (ID {expensive.car_id}), {expensive.price:.2f} грн"
    )
    print(
        f"Мінімальний пробіг: {cheapest_mileage.brand} {cheapest_mileage.model} "
        f"(ID {cheapest_mileage.car_id}), {cheapest_mileage.mileage} км"
    )
    print(f"Середня ціна: {report['average_price']:.2f} грн")
    mileage = report["mileage"]
    assert isinstance(mileage, analytics.MileageStatistics)
    print(
        f"Пробіг: min {mileage.minimum}, max {mileage.maximum}, середній {mileage.average:.1f}, "
        f"std {mileage.std:.1f}"
    )
    manufacturers = report["manufacturers"]
    assert isinstance(manufacturers, dict)
    print("Виробники (кількість / середня ціна):")
    for brand, statistics in manufacturers.items():
        print(f"  {brand:14} {statistics.count:6}  {statistics.average_price:12.2f}")
    print(f"Середня залишкова вартість через 10 років: {report['average_residual']:.2f} грн")
    print(f"Час catalog_report: {elapsed:.3f} с")


def show_profile(cars: list[CarRecord]) -> None:
    """cProfile: where the time goes; tracemalloc: memory; timeit: a small function."""
    title("2. cProfile: пошук bottleneck")
    report = profile_call(analytics.catalog_report, cars, limit=8)
    print("  ncalls   tottime   cumtime  function")
    for row in report.functions[:8]:
        print(f"{row.ncalls:>8} {row.tottime:9.3f} {row.cumtime:9.3f}  {row.name}")
    residual = report.find("residual_value")
    print(
        f"Усього під cProfile: {report.total_time:.3f} с; residual_values_sequential — "
        f"{report.share('residual_values_sequential'):.1%} часу"
    )
    print(
        f"Bottleneck: residual_value() — {residual.ncalls} викликів, tottime {residual.tottime:.3f} с "
        "(CPU-bound: 120 кроків обчислень на авто)"
    )
    after = profile_call(vectorized.catalog_report, vectorized.to_arrays(cars), limit=5)
    print(
        f"Після оптимізації (vectorized.catalog_report, NumPy): {after.total_time:.3f} с під cProfile; "
        f"residual_values — {after.share('residual_values'):.1%} часу, "
        f"{after.find('residual_values').ncalls} виклик"
    )

    title("3. tracemalloc і timeit")
    _, current, peak = measure_memory(generate_cars, len(cars))
    arrays, _, arrays_peak = measure_memory(vectorized.to_arrays, cars)
    print(f"list[CarRecord] з {len(cars)} авто: поточна {current:.2f} MB, пік {peak:.2f} MB")
    print(
        f"Масиви NumPy (5 стовпців): {arrays.nbytes / 1024 / 1024:.2f} MB, пік перетворення {arrays_peak:.2f} MB"
    )
    python_time = time_with_timeit(analytics.average_price, cars)
    numpy_time = time_with_timeit(vectorized.average_price, arrays)
    print(
        f"timeit average_price: цикл {python_time * 1000:.3f} мс, NumPy {numpy_time * 1000:.3f} мс "
        f"(у {calculate_speedup(python_time, numpy_time):.1f} раза швидше)"
    )


def show_cpu_bound(cars: list[CarRecord]) -> None:
    """The bottleneck with threads, processes and NumPy; every result is checked."""
    title(f"4. CPU-bound: залишкова вартість {len(cars)} авто ({os.cpu_count()} CPU)")
    base_time, expected = measure(analytics.residual_values_sequential, cars)
    print(f"Sequential:                {base_time:7.3f} с")
    threads_time, threads_result = measure(residual_values_threads, cars, WORKERS)
    print(
        f"ThreadPoolExecutor ({WORKERS}):    {threads_time:7.3f} с  speedup "
        f"{calculate_speedup(base_time, threads_time):.2f}  однакові: {threads_result == expected}"
    )
    processes_time, processes_result = measure(residual_values_processes, cars, WORKERS)
    print(
        f"ProcessPoolExecutor ({WORKERS}):   {processes_time:7.3f} с  speedup "
        f"{calculate_speedup(base_time, processes_time):.2f}  однакові: {processes_result == expected}"
    )
    arrays = vectorized.to_arrays(cars)
    numpy_time, numpy_result = measure(vectorized.residual_values, arrays)
    print(
        f"NumPy:                     {numpy_time:7.3f} с  speedup "
        f"{calculate_speedup(base_time, numpy_time):.2f}  "
        f"однакові (rtol 1e-9): {np.allclose(numpy_result, expected, rtol=1e-9)}"
    )
    process_sum = residual_sum_with_processes(cars, WORKERS)
    print(
        f"multiprocessing.Process ×{WORKERS} (сума через Queue): {process_sum:.2f}, "
        f"sequential: {sum(expected):.2f}"
    )


def show_files(cars: list[CarRecord]) -> None:
    """I/O-bound loading of 8 compressed files of the catalog."""
    title("5. I/O-bound: 8 файлів каталогу cars_part_N.csv.gz")
    with tempfile.TemporaryDirectory() as directory:
        paths = write_catalog_parts(cars, Path(directory), parts=8)
        size = sum(path.stat().st_size for path in paths) / 1024 / 1024
        print(f"Записано {len(paths)} файлів, {size:.2f} MB")
        base_time, texts = measure(read_parts_sequential, paths)
        threads_time, threads_texts = measure(read_parts_threads, paths, 8)
        manual_time, manual_texts = measure(read_parts_with_threading, paths)
        print(
            f"Читання + розпакування: послідовно {base_time:.4f} с; ThreadPoolExecutor (8) "
            f"{threads_time:.4f} с; threading.Thread ×8 {manual_time:.4f} с; "
            f"однакові: {texts == threads_texts == manual_texts}"
        )
        load_time, loaded = measure(load_parts_sequential, paths)
        load_threads_time, loaded_threads = measure(load_parts_threads, paths, 8)
        print(
            f"Повне завантаження з розбором CSV: послідовно {load_time:.3f} с; "
            f"ThreadPoolExecutor (8) {load_threads_time:.3f} с; авто: {len(loaded)}, "
            f"однакові: {loaded == loaded_threads == cars}"
        )


def show_race_condition(cars: list[CarRecord]) -> None:
    """Shared counter in 4 threads without Lock and with Lock."""
    title("6. Race condition: спільний лічильник оброблених авто, 4 потоки")
    batch, repeats, threads = cars[:10], 200_000, 4
    expected = threads * repeats * len(batch)
    print(f"Очікується: {expected}")
    for attempt in range(1, 6):
        result = count_in_threads(False, threads, batch, repeats)
        print(f"  без Lock, спроба {attempt}: {result}  втрачено {expected - result}")
    unsafe_time, _ = measure(count_in_threads, False, threads, batch, repeats)
    lock_time, locked = measure(count_in_threads, True, threads, batch, repeats)
    print(f"  з Lock: {locked}  правильно: {locked == expected}")
    print(f"Ціна синхронізації: без Lock {unsafe_time:.3f} с, з Lock {lock_time:.3f} с")


def show_cache(cars: list[CarRecord]) -> None:
    """lru_cache for brand statistics; the version of the catalog invalidates it."""
    title("7. Caching статистики марки (lru_cache + version)")
    clear_caches()
    catalog = CachedCarCatalog(cars)
    cold_time, cold = measure(catalog.brand_statistics, "Toyota")
    warm_time, warm = measure(catalog.brand_statistics, "toyota")
    print(
        f"Toyota: {cold.count} авто, середня ціна {cold.average_price:.2f}, max {cold.max_price:.2f}"
    )
    print(
        f"Перший виклик (miss): {cold_time * 1000:.3f} мс; повторний (hit): {warm_time * 1000:.4f} мс; "
        f"той самий об'єкт: {warm is cold}"
    )
    print(f"cache_info: hits/misses/size = {brand_cache_info()}")
    toyota = next(car for car in catalog.cars if car.brand == "Toyota")
    catalog.update_price(toyota.car_id, 5_000_000.0)
    changed = catalog.brand_statistics("Toyota")
    print(
        f"update_price(ID {toyota.car_id}, 5000000) → version {catalog.version}; "
        f"max {changed.max_price:.2f}, середня {changed.average_price:.2f}"
    )
    print(f"cache_info після зміни: {brand_cache_info()} (новий ключ — новий miss)")
    clear_caches()
    print(f"cache_clear(): {brand_cache_info()}")


def run_demo(count: int) -> None:
    """All parts of the demo on `count` generated cars."""
    elapsed, cars = measure(generate_cars, count)
    print("Лабораторна робота 9: продуктивність каталогу автомобілів (варіант 5)")
    print(f"Згенеровано {len(cars)} автомобілів (seed 42) за {elapsed:.3f} с")
    show_baseline(cars)
    show_profile(cars)
    show_cpu_bound(cars)
    show_files(cars)
    show_race_condition(cars)
    show_cache(cars)


def main(argv: list[str] | None = None) -> int:
    """Entry point; the optional argument is the number of cars."""
    args = sys.argv[1:] if argv is None else argv
    run_demo(int(args[0]) if args else DEFAULT_COUNT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
