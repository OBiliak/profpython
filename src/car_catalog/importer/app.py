"""Reliable import and export of the car catalog (laboratory work 5): python -m car_catalog.importer.app."""

import logging
import sys
from pathlib import Path

from car_catalog.importer.config import load_config
from car_catalog.importer.exceptions import (
    ApplicationError,
    ConfigurationError,
    RecordValidationError,
)
from car_catalog.importer.exporters import export_records
from car_catalog.importer.logging_config import configure_console_logging, configure_logging
from car_catalog.importer.models import AppConfig, InvalidRecord
from car_catalog.importer.readers import select_importer
from car_catalog.importer.services import ImportStatistics, import_vehicles, run_import
from car_catalog.importer.validators import ValidationPolicy

logger = logging.getLogger(__name__)


def show_statistics(config: AppConfig, statistics: ImportStatistics) -> None:
    """Print import statistics and the created files."""
    print("\n--- Статистика імпорту ---")
    print(f"Оброблено записів: {statistics.total}")
    print(f"Valid: {statistics.valid}, invalid: {statistics.invalid}")
    print(f"Відфільтровано за ціною: {statistics.filtered}, exported: {statistics.exported}")
    for path in (config.output.path, config.output.errors_path, config.output.summary_path):
        print(f"Файл: {path.as_posix()} ({path.stat().st_size} байт)")


def show_formats(config: AppConfig) -> None:
    """Show automatic format selection, JSON Lines, gzip and YAML input."""
    print("\n--- Єдиний interface: формат за розширенням ---")
    policy = ValidationPolicy.from_config(config.validation)
    source = config.output.path
    vehicles = [policy.parse(row, number) for number, row in select_importer(source).read(source)]
    print(f"{source.as_posix()} -> {type(select_importer(source)).__name__}: {len(vehicles)} записів")
    for name in ("vehicles.jsonl", "vehicles.json.gz"):
        path = source.with_name(name)
        written = export_records(vehicles, path)
        importer = select_importer(path)
        read_back = sum(1 for _ in importer.read(path))
        print(
            f"{path.as_posix()}: записано {written}, прочитано {read_back} "
            f"({type(importer).__name__}, {path.stat().st_size} байт)"
        )
    first_line = source.with_name("vehicles.jsonl").read_text(encoding="utf-8").splitlines()[0]
    print(f"Перший рядок JSON Lines: {first_line}")

    extra = config.input.path.with_name("vehicles_extra.yaml")
    print(f"\nYAML input {extra.as_posix()} -> {type(select_importer(extra)).__name__}:")
    statistics = ImportStatistics()
    errors: list[InvalidRecord] = []
    for vehicle in import_vehicles(
        select_importer(extra).read(extra),
        policy=policy,
        skip_invalid=True,
        statistics=statistics,
        errors=errors,
    ):
        print(f"  {vehicle.vehicle_id}: {vehicle.brand} {vehicle.model}, {vehicle.year}, {vehicle.price:.0f} грн")
    print(f"  valid={statistics.valid}, invalid={statistics.invalid}")


def main(argv: list[str] | None = None) -> int:
    """Run the import/export of laboratory work 5; return the exit code."""
    args = sys.argv[1:] if argv is None else argv
    config_path = Path(args[0]) if args else Path("config.yaml")
    configure_console_logging()
    print("=== Каталог автомобілів: імпорт та експорт (лабораторна робота №5, варіант 5) ===")
    try:
        config = load_config(config_path)
    except ConfigurationError as error:
        logger.error("Помилка конфігурації: %s (причина: %r)", error, error.__cause__)
        return 2
    configure_logging(config.logging)
    mode = "tolerant" if config.processing.skip_invalid else "strict"
    logger.info("Конфігурація %s, режим %s, input %s", config_path, mode, config.input.path)
    try:
        statistics = run_import(config)
    except RecordValidationError as error:
        logger.error(
            "Strict mode: імпорт зупинено на рядку %s, output не змінено", error.line_number
        )
        return 1
    except ApplicationError as error:
        logger.error("Критична помилка: %s", error)
        return 1
    show_statistics(config, statistics)
    show_formats(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
