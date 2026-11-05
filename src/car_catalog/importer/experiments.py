"""Experiments of laboratory work 5: strict/tolerant, streaming/eager, chaining, atomic output, config errors."""

import csv
import logging
import shutil
import time
import traceback
import tracemalloc
from collections.abc import Callable, Iterator
from pathlib import Path

import yaml

from car_catalog.importer.config import load_config
from car_catalog.importer.exceptions import ApplicationError, RecordValidationError
from car_catalog.importer.readers import FIELDS
from car_catalog.importer.services import ImportStatistics, run_import
from car_catalog.importer.validators import ValidationPolicy
from car_catalog.main import main

WORK_DIR = Path("data/generated/experiments")
BRANDS = ("Toyota", "Skoda", "BMW", "Volkswagen", "Hyundai", "Renault", "Kia")
SIZES = (10_000, 100_000, 500_000)


def write_vehicles_csv(path: Path, valid: int, invalid: int = 0) -> None:
    """Write a CSV with valid records and evenly spread invalid ones (price < 0)."""
    total = valid + invalid
    step = total // invalid if invalid else total + 1
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(FIELDS)
        for number in range(1, total + 1):
            price = -1 if number % step == 0 else 150_000 + number * 37 % 1_500_000
            brand = BRANDS[number % len(BRANDS)]
            writer.writerow([number, brand, "Model", 1995 + number % 31, price, number * 13 % 300_000])


def base_config(input_name: str, output_name: str, skip_invalid: bool) -> dict[str, object]:
    """Return a configuration dictionary for experiments inside WORK_DIR."""
    return {
        "schema_version": 1,
        "input": {"path": input_name},
        "output": {
            "path": output_name,
            "errors_path": "out/invalid.csv",
            "summary_path": "out/summary.json",
            "backup": False,
        },
        "validation": {"years": {"min": 1950, "max": 2026}},
        "filter": {"price": {"min": 0, "max": 5_000_000}},
        "processing": {"skip_invalid": skip_invalid, "progress_every": 100_000},
        "logging": {"level": "WARNING", "path": "logs/experiment.log"},
    }


def write_config(name: str, raw: dict[str, object]) -> Path:
    """Save a configuration dictionary as YAML in WORK_DIR."""
    path = WORK_DIR / name
    path.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def experiment_strict_tolerant() -> None:
    """Experiment 1: 1000 valid and 10 invalid records in strict and tolerant mode."""
    print("\n=== Експеримент 1. Strict vs tolerant (1000 valid + 10 invalid) ===")
    write_vehicles_csv(WORK_DIR / "strict_tolerant.csv", 1000, 10)
    results: dict[str, tuple[ImportStatistics, str, bool]] = {}
    for mode, skip_invalid in (("Strict", False), ("Tolerant", True)):
        output = f"out/{mode.lower()}.json"
        config_path = write_config(f"{mode.lower()}.yaml", base_config("strict_tolerant.csv", output, skip_invalid))
        statistics = ImportStatistics()
        try:
            run_import(load_config(config_path, {}), statistics)
            finish = "успішно, код 0"
        except RecordValidationError as error:
            finish = f"зупинено на рядку {error.line_number}, код 1"
        results[mode] = (statistics, finish, (WORK_DIR / output).exists())
    print(f"{'Параметр':<24} {'Strict':<28} {'Tolerant':<28}")
    rows: list[tuple[str, Callable[[ImportStatistics, str, bool], object]]] = [
        ("Оброблено записів", lambda s, f, e: s.total),
        ("Valid", lambda s, f, e: s.valid),
        ("Invalid", lambda s, f, e: s.invalid),
        ("Exported", lambda s, f, e: s.exported),
        ("Output-файл створено", lambda s, f, e: "так" if e else "ні"),
        ("Завершення application", lambda s, f, e: f),
    ]
    for title, value in rows:
        print(f"{title:<24} {value(*results['Strict'])!s:<28} {value(*results['Tolerant'])!s:<28}")


def eager_import(path: Path) -> list[dict[str, str]]:
    """Load all CSV rows into a list at once."""
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def streaming_import(path: Path) -> Iterator[dict[str, str]]:
    """Yield CSV rows one by one."""
    with path.open(encoding="utf-8", newline="") as file:
        yield from csv.DictReader(file)


def count_eager(path: Path) -> int:
    """Count rows loaded eagerly."""
    return len(eager_import(path))


def count_streaming(path: Path) -> int:
    """Count rows read in streaming mode (the generator is fully consumed)."""
    return sum(1 for _ in streaming_import(path))


def measure(action: Callable[[Path], int], path: Path) -> tuple[float, float, int]:
    """Return execution time (s), peak memory (MB) and the result of action."""
    start = time.perf_counter()
    result = action(path)
    elapsed = time.perf_counter() - start
    tracemalloc.start()
    action(path)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak / 1024 / 1024, result


def experiment_streaming_eager() -> None:
    """Experiment 2: execution time and peak memory of eager and streaming import."""
    print("\n=== Експеримент 2. Streaming vs eager (час без tracemalloc, peak RAM з tracemalloc) ===")
    print(f"{'Records':>8} | {'Eager time':>11} | {'Streaming time':>14} | {'Eager peak RAM':>14} | {'Streaming peak RAM':>18}")
    for size in SIZES:
        path = WORK_DIR / f"vehicles_{size}.csv"
        write_vehicles_csv(path, size)
        eager_time, eager_peak, eager_count = measure(count_eager, path)
        stream_time, stream_peak, stream_count = measure(count_streaming, path)
        assert eager_count == stream_count == size
        print(
            f"{size:>8} | {eager_time:>9.3f} с | {stream_time:>12.3f} с | "
            f"{eager_peak:>11.2f} MB | {stream_peak:>15.3f} MB"
        )


def describe_chain(error: BaseException) -> list[str]:
    """Return a short traceback of the exception chain (file names without full paths)."""
    chain: list[BaseException] = []
    current: BaseException | None = error
    while current is not None:
        chain.append(current)
        current = current.__cause__
    lines: list[str] = []
    for exception in reversed(chain):
        lines.append("Traceback (most recent call last):")
        for frame in traceback.extract_tb(exception.__traceback__):
            lines.append(f'  File "{Path(frame.filename).name}", line {frame.lineno}, in {frame.name}')
        lines.append(f"{type(exception).__module__}.{type(exception).__name__}: {exception}")
        if exception is not error:
            lines.append("\nThe above exception was the direct cause of the following exception:\n")
    return lines


def experiment_chaining() -> None:
    """Experiment 3: ValueError -> RecordValidationError with the original cause."""
    print("\n=== Експеримент 3. Exception chaining ===")
    row = {"vehicle_id": "1", "brand": "Toyota", "model": "Corolla", "year": "wrong",
           "price": "520000", "mileage": "85000"}
    print("CSV: vehicle_id,brand,model,year,price,mileage")
    print("     1,Toyota,Corolla,wrong,520000,85000")
    try:
        ValidationPolicy(1950, 2026).parse(row, line_number=2)
    except RecordValidationError as error:
        print("\n".join(describe_chain(error)))
        print(f"\nerror.__cause__: {type(error.__cause__).__name__}: {error.__cause__}")
        print(f"error.field = {error.field}, error.line_number = {error.line_number}")
        print(f"error.__suppress_context__ = {error.__suppress_context__}")


def experiment_atomic_output() -> None:
    """Experiment 4: an error during export does not damage the previous output."""
    print("\n=== Експеримент 4. Atomic output ===")
    write_vehicles_csv(WORK_DIR / "atomic_valid.csv", 50)
    write_vehicles_csv(WORK_DIR / "atomic_broken.csv", 40, 1)
    output = WORK_DIR / "out" / "atomic.json"
    good = write_config("atomic_good.yaml", base_config("atomic_valid.csv", "out/atomic.json", True))
    broken = write_config("atomic_broken.yaml", base_config("atomic_broken.csv", "out/atomic.json", False))
    run_import(load_config(good, {}))
    before = output.read_bytes()
    print(f"1) Попередній valid output: {output.as_posix()}, {len(before)} байт, 50 записів")
    print("2) Strict-імпорт файлу з invalid record у рядку 42 (exception під час запису JSON):")
    code = main([str(broken)])
    log_text = (WORK_DIR / "logs" / "experiment.log").read_text(encoding="utf-8")
    print(f"   код завершення main(): {code}")
    print(f"   output не пошкоджено: {output.read_bytes() == before}")
    print(f"   .tmp очищено: {not output.with_name(output.name + '.tmp').exists()}")
    print(f"   exception зареєстровано в log: {'RecordValidationError' in log_text}")
    print("3) OSError під час atomic replace (на місці output — каталог):")
    directory = WORK_DIR / "out" / "as_directory.json"
    directory.mkdir()
    raw = base_config("atomic_valid.csv", "out/as_directory.json", True)
    try:
        run_import(load_config(write_config("atomic_dir.yaml", raw), {}))
    except ApplicationError as error:
        print(f"   {type(error).__name__}: {error}")
        print(f"   причина (__cause__): {type(error.__cause__).__name__}")
        print(f"   .tmp очищено: {not directory.with_name(directory.name + '.tmp').exists()}")


def show_config_error(title: str, path: Path, environ: dict[str, str] | None = None) -> None:
    """Load a configuration and print the error and its cause."""
    try:
        load_config(path, environ or {})
        print(f"{title}: помилки немає")
    except ApplicationError as error:
        cause = type(error.__cause__).__name__ if error.__cause__ else "—"
        print(f"{title}:\n   {type(error).__name__}: {error}\n   cause: {cause}")


def experiment_config_errors() -> None:
    """Experiment 5: behaviour of the application with wrong configuration."""
    print("\n=== Експеримент 5. Configuration errors ===")
    write_vehicles_csv(WORK_DIR / "config_input.csv", 5)
    good = base_config("config_input.csv", "out/config.json", True)
    show_config_error("1. Відсутній config.yaml", WORK_DIR / "missing.yaml")
    broken = WORK_DIR / "broken.yaml"
    broken.write_text("input:\n  path: [data/vehicles.csv\n", encoding="utf-8")
    show_config_error("2. Неправильний YAML", broken)
    no_input = {key: value for key, value in good.items() if key != "input"}
    show_config_error("3. Немає ключа input", write_config("no_input.yaml", no_input))
    years = good | {"validation": {"years": {"min": 2030, "max": 2026}}}
    show_config_error("4. years.min = 2030 > max = 2026", write_config("years.yaml", years))
    missing_input = good | {"input": {"path": "no_such_file.csv"}}
    show_config_error("5. Input file відсутній", write_config("missing_input.yaml", missing_input))
    show_config_error("6. schema_version = 2", write_config("schema.yaml", good | {"schema_version": 2}))
    good_path = write_config("good.yaml", good)
    show_config_error("7. CAR_IMPORT_SKIP_INVALID=maybe", good_path, {"CAR_IMPORT_SKIP_INVALID": "maybe"})
    print("8. Output directory не існує:")
    new_output = good | {"output": {"path": "new_dir/sub/vehicles.json",
                                    "errors_path": "new_dir/invalid.csv",
                                    "summary_path": "new_dir/summary.json"}}
    target = WORK_DIR / "new_dir" / "sub"
    print(f"   до запуску {target.as_posix()} існує: {target.exists()}")
    statistics = run_import(load_config(write_config("new_dir.yaml", new_output), {}))
    print(f"   після запуску існує: {target.exists()}, exported={statistics.exported} (каталог створено автоматично)")


def run_experiments() -> None:
    """Run all experiments of laboratory work 5."""
    shutil.rmtree(WORK_DIR, ignore_errors=True)
    WORK_DIR.mkdir(parents=True)
    logging.basicConfig(level=logging.CRITICAL, force=True)
    experiment_strict_tolerant()
    experiment_streaming_eager()
    experiment_chaining()
    experiment_atomic_output()
    logging.basicConfig(level=logging.CRITICAL, force=True)
    experiment_config_errors()


if __name__ == "__main__":
    run_experiments()
