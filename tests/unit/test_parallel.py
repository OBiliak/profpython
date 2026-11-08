"""Tests for threads, processes, file loading and the Lock (laboratory work 9)."""

from pathlib import Path

import pytest

from car_catalog.performance.analytics import CarRecord, generate_cars, residual_values_sequential
from car_catalog.performance.parallel import (
    batch_residual_sum,
    count_in_threads,
    load_part,
    load_parts_sequential,
    load_parts_threads,
    read_parts_sequential,
    read_parts_threads,
    read_parts_with_threading,
    residual_sum_with_processes,
    residual_values_processes,
    residual_values_threads,
    split_batches,
    write_catalog_parts,
)


@pytest.fixture
def cars() -> list[CarRecord]:
    return generate_cars(3_000)


@pytest.mark.parametrize(("count", "parts", "sizes"), [(10, 3, [4, 4, 2]), (8, 4, [2, 2, 2, 2]), (2, 5, [1, 1])])
def test_split_batches_keeps_all_cars(count: int, parts: int, sizes: list[int]) -> None:
    cars = generate_cars(count)
    batches = split_batches(cars, parts)
    assert [len(batch) for batch in batches] == sizes
    assert [car for batch in batches for car in batch] == cars


@pytest.mark.parametrize("workers", [1, 2, 4])
def test_threads_give_the_same_residual_values(cars: list[CarRecord], workers: int) -> None:
    assert residual_values_threads(cars, workers) == residual_values_sequential(cars)


def test_catalog_parts_are_written_and_loaded_back(cars: list[CarRecord], tmp_path: Path) -> None:
    paths = write_catalog_parts(cars, tmp_path, parts=4)
    assert [path.name for path in paths] == [f"cars_part_{n}.csv.gz" for n in range(1, 5)]
    assert load_part(paths[0]) == cars[:750]
    assert load_parts_sequential(paths) == cars
    assert load_parts_threads(paths, workers=4) == cars


def test_reading_in_threads_keeps_order_of_files(cars: list[CarRecord], tmp_path: Path) -> None:
    paths = write_catalog_parts(cars, tmp_path, parts=6)
    texts = read_parts_sequential(paths)
    assert read_parts_threads(paths, workers=3) == texts
    assert read_parts_with_threading(paths) == texts
    assert texts[0].startswith("car_id,brand,model,year,price,mileage")


def test_lock_gives_exact_number_of_rows(cars: list[CarRecord]) -> None:
    batch = cars[:10]
    assert count_in_threads(True, threads=4, batch=batch, repeats=50_000) == 4 * 50_000 * 10


def test_unsafe_counter_never_counts_more_than_expected(cars: list[CarRecord]) -> None:
    # without Lock updates can be lost, so the result is not deterministic: only an upper bound
    result = count_in_threads(False, threads=4, batch=cars[:10], repeats=20_000)
    assert 0 < result <= 4 * 20_000 * 10


@pytest.mark.parametrize(("workers", "chunksize"), [(1, 500), (2, 1000), (4, 250)])
def test_processes_give_the_same_residual_values(
    cars: list[CarRecord], workers: int, chunksize: int
) -> None:
    assert residual_values_processes(cars, workers, chunksize) == residual_values_sequential(cars)


def test_multiprocessing_process_sum_matches_sequential(cars: list[CarRecord]) -> None:
    expected = sum(residual_values_sequential(cars))
    assert residual_sum_with_processes(cars, workers=3) == pytest.approx(expected)


def test_batch_residual_sum_of_empty_batch_is_zero() -> None:
    assert batch_residual_sum([]) == 0
