"""Cleaning and CSV parsing stages of the pipeline."""

import csv
from collections.abc import Iterable, Iterator

HEADER = ["id", "brand", "model", "year", "price", "mileage"]


def clean_lines(lines: Iterable[str]) -> Iterator[str]:
    """Yield stripped lines, skipping empty ones."""
    for line in lines:
        line = line.strip()
        if line:
            yield line


def parse_csv_rows(lines: Iterable[str]) -> Iterator[list[str]]:
    """Yield CSV rows as lists of strings, skipping header rows."""
    reader = csv.reader(lines)
    yield from (row for row in reader if row != HEADER)
