"""Tests for profiling helpers (cProfile, tracemalloc, timeit)."""

from car_catalog.performance.analytics import catalog_report, generate_cars
from car_catalog.performance.profiling import measure_memory, profile_call, time_with_timeit


def test_profile_finds_residual_values_as_bottleneck() -> None:
    cars = generate_cars(2_000)
    report = profile_call(catalog_report, cars)
    residual = report.find("residual_value")
    assert residual.ncalls == 2_000
    assert report.share("residual_values_sequential") > 0.5
    assert "cumtime" in report.text


def test_measure_memory_returns_result_and_peak() -> None:
    cars, current, peak = measure_memory(generate_cars, 5_000)
    assert len(cars) == 5_000
    assert peak >= current > 0


def test_time_with_timeit_is_positive() -> None:
    assert time_with_timeit(sum, [1, 2, 3], number=10, repeat=2) > 0
