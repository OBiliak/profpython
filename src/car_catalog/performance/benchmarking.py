"""Small benchmark framework: repeated perf_counter measurements, speedup, CSV of results."""

import csv
import statistics
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any


@dataclass
class BenchmarkResult:
    """Times of all runs of one experiment."""

    experiment: str
    method: str
    data_size: int
    workers: int | None
    times: list[float] = field(default_factory=list)
    peak_memory_mb: float | None = None
    speedup: float | None = None

    @property
    def mean(self) -> float:
        """Average time of the runs."""
        return statistics.mean(self.times)

    @property
    def median(self) -> float:
        """Median time of the runs."""
        return statistics.median(self.times)


def measure(function: Callable[..., Any], *args: Any) -> tuple[float, Any]:
    """Run the function once; return (elapsed seconds, result)."""
    start = perf_counter()
    result = function(*args)
    return perf_counter() - start, result


def benchmark_repeated(function: Callable[..., Any], *args: Any, repeats: int = 5) -> tuple[list[float], Any]:
    """Run the function `repeats` times; return all times and the last result."""
    times = []
    result = None
    for _ in range(repeats):
        elapsed, result = measure(function, *args)
        times.append(elapsed)
    return times, result


def calculate_speedup(baseline: float, optimized: float) -> float:
    """speedup = baseline time / optimized time (> 1 — faster, < 1 — slower)."""
    return baseline / optimized


def add_speedups(results: list[BenchmarkResult], baseline_method: str) -> None:
    """Speedup of every result against the baseline method of the same experiment and data size."""
    baselines = {
        (item.experiment, item.data_size): item.mean for item in results if item.method == baseline_method
    }
    for item in results:
        base = baselines.get((item.experiment, item.data_size))
        if base is not None:
            item.speedup = calculate_speedup(base, item.mean)


def save_csv(results: list[BenchmarkResult], path: Path) -> None:
    """Save the results: one row per experiment, the runs in columns run_1..run_N."""
    path.parent.mkdir(parents=True, exist_ok=True)
    runs = max(len(item.times) for item in results)
    header = ["experiment", "method", "data_size", "workers"]
    header += [f"run_{number}" for number in range(1, runs + 1)]
    header += ["mean", "median", "peak_memory_mb", "speedup"]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        for item in results:
            writer.writerow(
                [item.experiment, item.method, item.data_size, item.workers or "-"]
                + [f"{value:.6f}" for value in item.times]
                + [""] * (runs - len(item.times))
                + [f"{item.mean:.6f}", f"{item.median:.6f}",
                   "" if item.peak_memory_mb is None else f"{item.peak_memory_mb:.2f}",
                   "" if item.speedup is None else f"{item.speedup:.2f}"]
            )
