"""Benchmark of search by ID in list and dict and membership in list and set."""

import random
import timeit
from collections.abc import Callable

from car_catalog.processors import create_car_index, find_car_by_id, find_car_linear

SIZES = (1_000, 10_000, 100_000)
BRANDS = ("Toyota", "Volkswagen", "Skoda", "BMW", "Renault", "Honda", "Audi", "Ford")
SEARCHES = 100
REPEATS = 5


def generate_cars(count: int) -> list[dict]:
    """Return a list of random car records with IDs from 1 to count."""
    random.seed(42)
    return [
        {
            "id": car_id,
            "brand": random.choice(BRANDS),
            "model": f"Model-{car_id}",
            "year": random.randint(2005, 2026),
            "price": float(random.randint(150_000, 2_500_000)),
            "mileage": random.randint(0, 300_000),
        }
        for car_id in range(1, count + 1)
    ]


def measure(statement: Callable[[], object], searches: int = SEARCHES) -> float:
    """Return the best time of one call in microseconds over several repeats."""
    times = timeit.repeat(statement, number=searches, repeat=REPEATS)
    return min(times) / searches * 1_000_000


def run_benchmark() -> list[tuple[int, float, float, float, float]]:
    """Return rows: size, list search, dict search, list membership, set membership."""
    rows = []
    for size in SIZES:
        cars = generate_cars(size)
        index = create_car_index(cars)
        models = [car["model"] for car in cars]
        model_set = set(models)
        last_id = size
        list_time = measure(lambda: find_car_linear(cars, last_id))
        dict_time = measure(lambda: find_car_by_id(index, last_id))
        list_in_time = measure(lambda: "Unknown" in models)
        set_in_time = measure(lambda: "Unknown" in model_set)
        rows.append((size, list_time, dict_time, list_in_time, set_in_time))
    return rows


def print_table(rows: list[tuple[int, float, float, float, float]]) -> None:
    """Print benchmark results as a text table."""
    print("Пошук останнього ID і перевірка відсутньої моделі, час одного виклику, мкс")
    print(f"(найкращий з {REPEATS} повторів по {SEARCHES} викликів)")
    print()
    print(
        f"{'Records':>8} | {'list search':>11} | {'dict search':>11} | "
        f"{'list/dict':>9} | {'x in list':>9} | {'x in set':>8}"
    )
    print("-" * 72)
    for size, list_time, dict_time, list_in_time, set_in_time in rows:
        print(
            f"{size:>8} | {list_time:>11.3f} | {dict_time:>11.3f} | "
            f"{list_time / dict_time:>8.0f}x | {list_in_time:>9.3f} | {set_in_time:>8.3f}"
        )


def main() -> None:
    """Run the benchmark and print the table."""
    print_table(run_benchmark())


if __name__ == "__main__":
    main()
