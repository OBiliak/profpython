"""Batch processing of a stream of car records."""

from collections.abc import Iterable, Iterator
from itertools import islice

from car_catalog.stream.models import CarRecord


def batched_cars(cars: Iterable[CarRecord], batch_size: int) -> Iterator[list[CarRecord]]:
    """Yield lists of at most batch_size cars from a stream."""
    if batch_size <= 0:
        raise ValueError("Розмір batch має бути більшим за нуль.")
    iterator = iter(cars)
    while True:
        batch = list(islice(iterator, batch_size))
        if not batch:
            return
        yield batch
