"""Generation of large CSV datasets of cars for streaming experiments."""

import csv
import random
from collections.abc import Iterator
from itertools import islice
from pathlib import Path

from car_catalog.stream.iterators import generate_ids
from car_catalog.stream.parsers import HEADER

DATA_DIR = Path("data/generated")
MODELS = {
    "Toyota": ("Corolla", "Camry", "RAV4", "Yaris"),
    "Volkswagen": ("Golf", "Passat", "Tiguan"),
    "Skoda": ("Octavia", "Fabia", "Superb"),
    "BMW": ("X5", "320i", "520d"),
    "Renault": ("Logan", "Megane", "Duster"),
    "Honda": ("Civic", "CR-V"),
    "Ford": ("Focus", "Kuga"),
    "Kia": ("Sportage", "Ceed"),
}
INVALID_SHARE = 0.01


def generate_rows(count: int, seed: int = 42) -> Iterator[list[str]]:
    """Yield count CSV rows of cars, about 1% of them invalid."""
    rng = random.Random(seed)
    brands = list(MODELS)
    for car_id in islice(generate_ids(), count):
        brand = rng.choice(brands)
        year = str(rng.randint(2005, 2026))
        if rng.random() < INVALID_SHARE:
            year = "unknown"
        yield [
            str(car_id),
            brand,
            rng.choice(MODELS[brand]),
            year,
            str(rng.randint(150, 2500) * 1000),
            str(rng.randint(0, 300) * 1000),
        ]


def write_dataset(path: Path, count: int) -> Path:
    """Write a generated dataset to a CSV file row by row and return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(HEADER)
        writer.writerows(generate_rows(count))
    return path


def ensure_dataset(count: int) -> Path:
    """Return the path of a dataset with count records, creating it if needed."""
    path = DATA_DIR / f"cars_{count}.csv"
    if not path.exists():
        write_dataset(path, count)
    return path
