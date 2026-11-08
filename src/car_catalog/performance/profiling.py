"""Profiling of the catalog: cProfile (where the time goes) and tracemalloc (how much memory)."""

import cProfile
import io
import pstats
import timeit
import tracemalloc
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

MB = 1024 * 1024


@dataclass(frozen=True)
class FunctionProfile:
    """One row of cProfile statistics."""

    name: str
    ncalls: int
    tottime: float
    cumtime: float


@dataclass(frozen=True)
class ProfileReport:
    """Result of profiling: total time, rows sorted by cumtime and the pstats text."""

    total_time: float
    functions: list[FunctionProfile]
    text: str

    def find(self, name: str) -> FunctionProfile:
        """Row of a function by its name."""
        return next(item for item in self.functions if item.name == name)

    def share(self, name: str) -> float:
        """Part of the total time spent in a function with its callees (cumtime / total)."""
        return self.find(name).cumtime / self.total_time


def profile_call(function: Callable[..., Any], *args: Any, limit: int = 12) -> ProfileReport:
    """Run the function under cProfile; rows are sorted by cumulative time."""
    profiler = cProfile.Profile()
    profiler.enable()
    function(*args)
    profiler.disable()
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats("cumulative").print_stats(limit)
    rows = []
    for (_, _, name), (_, ncalls, tottime, cumtime, _) in stats.stats.items():  # type: ignore[attr-defined]
        rows.append(FunctionProfile(name, ncalls, tottime, cumtime))
    rows.sort(key=lambda item: item.cumtime, reverse=True)
    return ProfileReport(stats.total_tt, rows, stream.getvalue())  # type: ignore[attr-defined]


def measure_memory(function: Callable[..., Any], *args: Any) -> tuple[Any, float, float]:
    """Run the function under tracemalloc; return (result, current MB, peak MB)."""
    tracemalloc.start()
    try:
        result = function(*args)
        current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return result, current / MB, peak / MB


def time_with_timeit(
    function: Callable[..., Any], *args: Any, number: int = 5, repeat: int = 3
) -> float:
    """The best average time of one call: min over `repeat` series of `number` calls (timeit)."""
    timer = timeit.Timer(lambda: function(*args))
    return min(timer.repeat(repeat=repeat, number=number)) / number
