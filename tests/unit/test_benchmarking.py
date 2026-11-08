"""Tests for the benchmark helpers."""

import csv
from pathlib import Path

import pytest

from car_catalog.performance.benchmarking import (
    BenchmarkResult,
    add_speedups,
    benchmark_repeated,
    calculate_speedup,
    measure,
    save_csv,
)


def test_measure_returns_time_and_result() -> None:
    elapsed, result = measure(sum, [1, 2, 3])
    assert result == 6
    assert elapsed >= 0


def test_benchmark_repeated_runs_function_n_times() -> None:
    calls = []
    times, result = benchmark_repeated(lambda: calls.append(1) or len(calls), repeats=4)
    assert len(times) == 4
    assert result == 4


@pytest.mark.parametrize(("baseline", "optimized", "expected"), [(4.0, 1.0, 4.0), (1.0, 2.0, 0.5)])
def test_calculate_speedup(baseline: float, optimized: float, expected: float) -> None:
    assert calculate_speedup(baseline, optimized) == expected


def test_mean_median_and_speedups() -> None:
    results = [
        BenchmarkResult("cpu", "Sequential", 100, None, [3.0, 4.0, 5.0]),
        BenchmarkResult("cpu", "Processes", 100, 4, [1.0, 1.0, 2.5]),
        BenchmarkResult("cpu", "Processes", 200, 4, [1.0]),
    ]
    add_speedups(results, "Sequential")
    assert results[1].mean == 1.5
    assert results[1].median == 1.0
    assert results[0].speedup == 1.0
    assert results[1].speedup == pytest.approx(4.0 / 1.5)
    assert results[2].speedup is None  # no baseline for this data size


def test_save_csv_writes_all_runs(tmp_path: Path) -> None:
    path = tmp_path / "results" / "benchmark.csv"
    results = [
        BenchmarkResult("cpu", "Sequential", 10, None, [2.0, 2.0], peak_memory_mb=1.5, speedup=1.0),
        BenchmarkResult("cpu", "Threads", 10, 2, [1.0]),
    ]
    save_csv(results, path)
    with path.open(encoding="utf-8") as file:
        rows = list(csv.reader(file))
    assert rows[0] == [
        "experiment",
        "method",
        "data_size",
        "workers",
        "run_1",
        "run_2",
        "mean",
        "median",
        "peak_memory_mb",
        "speedup",
    ]
    assert rows[1] == [
        "cpu",
        "Sequential",
        "10",
        "-",
        "2.000000",
        "2.000000",
        "2.000000",
        "2.000000",
        "1.50",
        "1.00",
    ]
    assert rows[2][4:6] == ["1.000000", ""]
    assert rows[2][-2:] == ["", ""]
