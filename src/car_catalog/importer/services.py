"""Import service: streaming validation, strict/tolerant modes, filtering and statistics."""

import logging
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from car_catalog.importer.exceptions import RecordValidationError
from car_catalog.importer.exporters import export_errors, export_records, export_summary
from car_catalog.importer.files import logged_operation
from car_catalog.importer.models import AppConfig, InvalidRecord, VehicleRecord
from car_catalog.importer.readers import select_importer
from car_catalog.importer.validators import ValidationPolicy

logger = logging.getLogger(__name__)


@dataclass
class ImportStatistics:
    """Counters of processed, valid, invalid, filtered and exported records."""

    total: int = 0
    valid: int = 0
    invalid: int = 0
    filtered: int = 0
    exported: int = 0


def import_vehicles(
    rows: Iterable[tuple[int, dict[str, Any]]],
    *,
    policy: ValidationPolicy,
    skip_invalid: bool,
    statistics: ImportStatistics,
    errors: list[InvalidRecord],
    progress_every: int = 1000,
) -> Iterator[VehicleRecord]:
    """Yield valid vehicles one by one; skip (tolerant) or stop (strict) on invalid rows."""
    for line_number, row in rows:
        if statistics.total and statistics.total % progress_every == 0:
            logger.info(
                "Прогрес: оброблено %s, valid=%s, invalid=%s",
                statistics.total, statistics.valid, statistics.invalid,
            )
        statistics.total += 1
        try:
            vehicle = policy.parse(row, line_number)
        except RecordValidationError as error:
            statistics.invalid += 1
            logger.warning("Некоректний запис у рядку %s: %s", error.line_number, error)
            if not skip_invalid:
                raise
            errors.append(InvalidRecord(line_number, row, str(error)))
            continue
        statistics.valid += 1
        yield vehicle


def filter_by_price(
    vehicles: Iterable[VehicleRecord],
    min_price: float,
    max_price: float,
    statistics: ImportStatistics,
) -> Iterator[VehicleRecord]:
    """Yield vehicles whose price is inside the configured range."""
    for vehicle in vehicles:
        if min_price <= vehicle.price <= max_price:
            yield vehicle
        else:
            statistics.filtered += 1
            logger.info(
                "Відфільтровано ID %s: ціна %.0f грн поза діапазоном",
                vehicle.vehicle_id, vehicle.price,
            )


def build_summary(
    config: AppConfig, statistics: ImportStatistics, errors: list[InvalidRecord]
) -> dict[str, object]:
    """Collect the export summary report."""
    return {
        "created_at": datetime.now(),
        "input": config.input.path,
        "output": config.output.path,
        "mode": "tolerant" if config.processing.skip_invalid else "strict",
        "statistics": asdict(statistics),
        "invalid_lines": [invalid.line_number for invalid in errors],
    }


def run_import(config: AppConfig) -> ImportStatistics:
    """Import, validate, filter and export vehicles according to the configuration."""
    statistics = ImportStatistics()
    errors: list[InvalidRecord] = []
    policy = ValidationPolicy.from_config(config.validation)
    importer = select_importer(config.input.path)
    with logged_operation("Імпорт/експорт каталогу автомобілів"):
        vehicles = import_vehicles(
            importer.read(config.input.path),
            policy=policy,
            skip_invalid=config.processing.skip_invalid,
            statistics=statistics,
            errors=errors,
            progress_every=config.processing.progress_every,
        )
        selected = filter_by_price(
            vehicles, config.filter.min_price, config.filter.max_price, statistics
        )
        statistics.exported = export_records(
            selected, config.output.path, backup=config.output.backup
        )
        export_errors(errors, config.output.errors_path)
        export_summary(build_summary(config, statistics, errors), config.output.summary_path)
    logger.info(
        "Total=%s, valid=%s, invalid=%s, filtered=%s, exported=%s",
        statistics.total, statistics.valid, statistics.invalid,
        statistics.filtered, statistics.exported,
    )
    return statistics
