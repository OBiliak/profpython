"""Lazy pipeline: reader -> cleaning -> parsing -> validation -> filtering -> transformation."""

from collections import Counter
from collections.abc import Iterable, Iterator
from pathlib import Path

from car_catalog.config import MAX_YEAR
from car_catalog.stream.filters import filter_by_brand, filter_by_year, validate_cars
from car_catalog.stream.models import CarRecord
from car_catalog.stream.parsers import clean_lines, parse_csv_rows
from car_catalog.stream.readers import read_many_files
from car_catalog.stream.transformations import normalize_cars


def build_pipeline(
    paths: Iterable[Path],
    stats: Counter,
    brands: set[str] | None = None,
    min_year: int | None = None,
    max_year: int = MAX_YEAR,
) -> Iterator[CarRecord]:
    """Return a lazy stream of valid, filtered and normalized cars from CSV files."""
    lines = read_many_files(paths)
    rows = parse_csv_rows(clean_lines(lines))
    cars = validate_cars(rows, stats)
    if brands:
        cars = filter_by_brand(cars, brands)
    if min_year is not None:
        cars = filter_by_year(cars, min_year, max_year)
    return normalize_cars(cars)
