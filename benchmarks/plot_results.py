"""Charts of benchmark results: python benchmarks/plot_results.py (needs pip install -e ".[bench]")."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # files only, no window
import matplotlib.pyplot as plt  # noqa: E402

RESULTS = Path(__file__).parent / "results"
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
GRID, TEXT, MUTED = "#e4e3df", "#0b0b0b", "#52514e"


def load(path: Path) -> list[dict[str, str]]:
    """Rows of benchmark_results.csv."""
    with path.open(encoding="utf-8") as file:
        return list(csv.DictReader(file))


def label(row: dict[str, str]) -> str:
    """Method with the number of workers: 'Processes (4)'."""
    return row["method"] if row["workers"] == "-" else f"{row['method']} ({row['workers']})"


def number(value: int) -> str:
    """250000 → '250 000'."""
    return f"{value:,}".replace(",", " ")


def style(axis: plt.Axes, title: str, xlabel: str, ylabel: str) -> None:
    """Recessive axes and grid, text in neutral ink."""
    axis.set_title(title, loc="left", color=TEXT, fontsize=12)
    axis.set_xlabel(xlabel, color=MUTED)
    axis.set_ylabel(ylabel, color=MUTED)
    axis.grid(color=GRID, linewidth=1)
    axis.set_axisbelow(True)
    for side in ("top", "right"):
        axis.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        axis.spines[side].set_color(GRID)
    axis.tick_params(colors=MUTED)


def plot_time(rows: list[dict[str, str]], size: int, path: Path) -> None:
    """Mean time of every residual-value method on the largest data set."""
    selected = [r for r in rows if r["experiment"] == "residual" and int(r["data_size"]) == size]
    names = [label(r) for r in selected][::-1]
    times = [float(r["mean"]) for r in selected][::-1]
    figure, axis = plt.subplots(figsize=(8, 5))
    bars = axis.barh(names, times, height=0.6, color=BLUE)
    for bar, value in zip(bars, times):
        axis.text(
            bar.get_width() + max(times) * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.2f} с",
            va="center",
            color=TEXT,
            fontsize=9,
        )
    style(axis, f"Залишкова вартість, {number(size)} авто: середній час (5 повторів)", "час, с", "")
    axis.grid(axis="y", visible=False)
    axis.set_xlim(0, max(times) * 1.15)
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def plot_speedup(rows: list[dict[str, str]], size: int, path: Path) -> None:
    """Speedup of threads and processes against the number of workers."""
    figure, axis = plt.subplots(figsize=(8, 5))
    axis.axhline(1, color=GRID, linewidth=1.5, zorder=1)
    workers: list[int] = []
    for method, name, color in (
        ("Processes", "ProcessPoolExecutor", ORANGE),
        ("Threads", "ThreadPoolExecutor", BLUE),
    ):
        selected = [
            r
            for r in rows
            if r["experiment"] == "residual"
            and r["method"] == method
            and int(r["data_size"]) == size
        ]
        workers = [int(r["workers"]) for r in selected]
        speedups = [float(r["speedup"]) for r in selected]
        axis.plot(
            workers,
            speedups,
            color=color,
            linewidth=2,
            marker="o",
            markersize=7,
            markeredgecolor="white",
            markeredgewidth=2,
            label=name,
            zorder=3,
        )
        axis.annotate(
            f"{speedups[-1]:.2f}×",
            (workers[-1], speedups[-1]),
            xytext=(8, 0),
            textcoords="offset points",
            va="center",
            color=TEXT,
            fontsize=9,
        )
    axis.plot(
        workers,
        workers,
        color=MUTED,
        linewidth=1,
        linestyle="--",
        label="ідеальне (= workers)",
        zorder=2,
    )
    axis.set_xticks(workers)
    style(
        axis,
        f"Прискорення відносно Sequential, {number(size)} авто",
        "кількість workers",
        "speedup, ×",
    )
    axis.legend(frameon=False, labelcolor=TEXT)
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def plot_sizes(rows: list[dict[str, str]], path: Path) -> None:
    """Time against data size for the main methods (log scales)."""
    figure, axis = plt.subplots(figsize=(8, 5))
    series = [
        ("Sequential", "-", BLUE),
        ("Threads", "8", ORANGE),
        ("Processes", "8", AQUA),
        ("NumPy", "-", YELLOW),
    ]
    sequential: list[float] = []
    for method, workers, color in series:
        selected = [
            r
            for r in rows
            if r["experiment"] == "residual" and r["method"] == method and r["workers"] == workers
        ]
        sizes = [int(r["data_size"]) for r in selected]
        times = [float(r["mean"]) for r in selected]
        if method == "Sequential":
            sequential = times
        name = method if workers == "-" else f"{method} ({workers})"
        axis.plot(
            sizes,
            times,
            color=color,
            linewidth=2,
            marker="o",
            markersize=7,
            markeredgecolor="white",
            markeredgewidth=2,
            label=name,
        )
    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set_xticks(sizes, [number(size) for size in sizes])
    axis.minorticks_off()
    axis.annotate(
        "Threads (8) ≈ Sequential: лінії збігаються (GIL)",
        (sizes[1], sequential[1]),
        xytext=(0, 14),
        textcoords="offset points",
        ha="center",
        color=TEXT,
        fontsize=9,
    )
    style(axis, "Залишкова вартість: час від розміру даних", "кількість автомобілів", "час, с")
    axis.legend(frameon=False, labelcolor=TEXT)
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def main() -> None:
    rows = load(RESULTS / "benchmark_results.csv")
    size = max(int(r["data_size"]) for r in rows if r["experiment"] == "residual")
    plot_time(rows, size, RESULTS / "execution_time.png")
    plot_speedup(rows, size, RESULTS / "speedup.png")
    plot_sizes(rows, RESULTS / "time_by_size.png")
    print(f"Графіки збережено в {RESULTS}")


if __name__ == "__main__":
    main()
