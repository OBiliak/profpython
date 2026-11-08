"""Threads and processes: CPU-bound residual values, I/O-bound loading of catalog files, Lock."""

from __future__ import annotations

import csv
import gzip
import io
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path
from threading import Lock, Thread

from car_catalog.performance.analytics import CarRecord, car_residual_value

FIELDS = ("car_id", "brand", "model", "year", "price", "mileage")


def split_batches(cars: list[CarRecord], parts: int) -> list[list[CarRecord]]:
    """Split the catalog into `parts` batches of almost equal size."""
    size = -(-len(cars) // parts)  # rounding up
    return [cars[start:start + size] for start in range(0, len(cars), size)]


# --- CPU-bound: residual values ---


def batch_residual_values(batch: list[CarRecord]) -> list[float]:
    """Residual values of one batch of cars."""
    return [car_residual_value(car) for car in batch]


def residual_values_threads(cars: list[CarRecord], workers: int) -> list[float]:
    """Residual values in a ThreadPoolExecutor, one batch per thread.

    Batches, not single cars: map over 250 000 items creates 250 000 Future objects
    (chunksize works only for processes). Because of the GIL there is still no speedup.
    """
    with ThreadPoolExecutor(max_workers=workers) as executor:
        parts = list(executor.map(batch_residual_values, split_batches(cars, workers)))
    return [value for part in parts for value in part]


def residual_values_processes(
    cars: list[CarRecord], workers: int, chunksize: int = 2000
) -> list[float]:
    """Residual values in a ProcessPoolExecutor: every process has its own interpreter and GIL.

    chunksize sends cars to the processes in batches, not one by one (fewer pickle transfers).
    """
    with ProcessPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(car_residual_value, cars, chunksize=chunksize))


def batch_residual_sum(batch: list[CarRecord]) -> float:
    """Sum of residual values of one batch."""
    return sum(car_residual_value(car) for car in batch)


def _process_worker(
    index: int, batch: list[CarRecord], results: multiprocessing.Queue[tuple[int, float]]
) -> None:
    """Target of multiprocessing.Process: put (batch number, sum) into the queue."""
    results.put((index, batch_residual_sum(batch)))


def residual_sum_with_processes(cars: list[CarRecord], workers: int) -> float:
    """multiprocessing.Process without a pool: start(), results through Queue, join()."""
    results: multiprocessing.Queue[tuple[int, float]] = multiprocessing.Queue()
    processes = [
        multiprocessing.Process(target=_process_worker, args=(index, batch, results))
        for index, batch in enumerate(split_batches(cars, workers))
    ]
    for process in processes:
        process.start()
    sums = dict(results.get() for _ in processes)  # read before join, otherwise the queue can block
    for process in processes:
        process.join()
    return sum(sums[index] for index in sorted(sums))


# --- I/O-bound: several compressed catalog files ---


def write_catalog_parts(cars: list[CarRecord], directory: Path, parts: int = 8) -> list[Path]:
    """Save the catalog as `parts` files cars_part_N.csv.gz."""
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for number, batch in enumerate(split_batches(cars, parts), start=1):
        path = directory / f"cars_part_{number}.csv.gz"
        with gzip.open(path, "wt", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(FIELDS)
            for car in batch:
                writer.writerow((car.car_id, car.brand, car.model, car.year, car.price, car.mileage))
        paths.append(path)
    return paths


def read_part_text(path: Path) -> str:
    """I/O stage: read the file and unpack it (zlib releases the GIL while it works)."""
    return gzip.decompress(path.read_bytes()).decode("utf-8")


def parse_part(text: str) -> list[CarRecord]:
    """CPU stage: turn CSV text into CarRecord objects (pure Python, holds the GIL)."""
    return [
        CarRecord(
            int(row["car_id"]), row["brand"], row["model"],
            int(row["year"]), float(row["price"]), int(row["mileage"]),
        )
        for row in csv.DictReader(io.StringIO(text))
    ]


def load_part(path: Path) -> list[CarRecord]:
    """Read and parse one compressed file of the catalog."""
    return parse_part(read_part_text(path))


def read_parts_sequential(paths: list[Path]) -> list[str]:
    """Baseline of the I/O stage: files one after another."""
    return [read_part_text(path) for path in paths]


def read_parts_threads(paths: list[Path], workers: int) -> list[str]:
    """I/O stage in a ThreadPoolExecutor; map keeps the order of files."""
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(read_part_text, paths))


def read_parts_with_threading(paths: list[Path]) -> list[str]:
    """threading.Thread without a pool: one thread per file, start() and join()."""
    texts = [""] * len(paths)

    def read_into(index: int, path: Path) -> None:
        texts[index] = read_part_text(path)

    threads = [Thread(target=read_into, args=(index, path)) for index, path in enumerate(paths)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return texts


def load_parts_sequential(paths: list[Path]) -> list[CarRecord]:
    """Full loading (reading + parsing) of all files one after another."""
    cars: list[CarRecord] = []
    for path in paths:
        cars.extend(load_part(path))
    return cars


def load_parts_threads(paths: list[Path], workers: int) -> list[CarRecord]:
    """Full loading in threads: parsing holds the GIL, so the gain is small."""
    with ThreadPoolExecutor(max_workers=workers) as executor:
        parts = list(executor.map(load_part, paths))
    return [car for part in parts for car in part]


# --- Race condition and Lock ---


class RowCounter:
    """Shared counter of processed cars (one object for all threads)."""

    def __init__(self) -> None:
        self.rows = 0
        self.lock = Lock()


def count_rows(batch: list[CarRecord]) -> int:
    """Number of cars in a batch (a function call between read and write of the counter)."""
    return len(batch)


def add_rows_unsafe(counter: RowCounter, batch: list[CarRecord], repeats: int) -> None:
    """read → count_rows() → write without a lock: another thread may write in between."""
    for _ in range(repeats):
        counter.rows = counter.rows + count_rows(batch)


def add_rows_with_lock(counter: RowCounter, batch: list[CarRecord], repeats: int) -> None:
    """The same, but read and write are a critical section under Lock."""
    for _ in range(repeats):
        with counter.lock:
            counter.rows = counter.rows + count_rows(batch)


def count_in_threads(locked: bool, threads: int, batch: list[CarRecord], repeats: int) -> int:
    """Start `threads` threads that add rows to one counter; return the final value."""
    counter = RowCounter()
    target = add_rows_with_lock if locked else add_rows_unsafe
    workers = [Thread(target=target, args=(counter, batch, repeats)) for _ in range(threads)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    return counter.rows
