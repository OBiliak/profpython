"""Atomic export of vehicles to JSON and JSON Lines, error CSV and summary report."""

import csv
import json
from collections.abc import Iterable
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol, TextIO

from car_catalog.importer.exceptions import DataExportError
from car_catalog.importer.files import AtomicWriter
from car_catalog.importer.models import InvalidRecord, VehicleRecord
from car_catalog.importer.readers import FIELDS, data_suffix


class VehicleJSONEncoder(json.JSONEncoder):
    """JSON encoder that also understands dataclasses, Path and datetime."""

    def default(self, o: object) -> object:
        """Convert objects that json cannot serialize by itself."""
        if is_dataclass(o) and not isinstance(o, type):
            return asdict(o)
        if isinstance(o, Path):
            return o.as_posix()
        if isinstance(o, datetime):
            return o.isoformat(timespec="seconds")
        return super().default(o)


def to_json(value: object, indent: int | None = None) -> str:
    """Serialize a value with the custom encoder, keeping Ukrainian letters."""
    return json.dumps(value, cls=VehicleJSONEncoder, ensure_ascii=False, indent=indent)


class Exporter(Protocol):
    """Writes vehicle records to an open text file."""

    def write(self, records: Iterable[VehicleRecord], file: TextIO) -> int:
        """Write records and return their count."""
        ...


class JsonExporter:
    """Writes a JSON array record by record (streaming output)."""

    def write(self, records: Iterable[VehicleRecord], file: TextIO) -> int:
        """Write records as a JSON array."""
        count = 0
        file.write("[")
        for record in records:
            file.write(",\n" if count else "\n")
            file.write(to_json(record, indent=2))
            count += 1
        file.write("\n]\n")
        return count


class JsonLinesExporter:
    """Writes one JSON object per line."""

    def write(self, records: Iterable[VehicleRecord], file: TextIO) -> int:
        """Write records in JSON Lines format."""
        count = 0
        for record in records:
            file.write(to_json(record) + "\n")
            count += 1
        return count


EXPORTERS: dict[str, Exporter] = {".json": JsonExporter(), ".jsonl": JsonLinesExporter()}


def select_exporter(path: Path) -> Exporter:
    """Choose the exporter by the file extension."""
    try:
        return EXPORTERS[data_suffix(path)]
    except KeyError as error:
        raise DataExportError(f"Непідтримуваний формат вихідного файлу: {path.name}") from error


def export_records(
    records: Iterable[VehicleRecord], path: Path, *, backup: bool = False
) -> int:
    """Export records atomically; the old output stays intact if an error occurs."""
    exporter = select_exporter(path)
    try:
        with AtomicWriter(path, backup=backup) as file:
            return exporter.write(records, file)
    except (OSError, TypeError) as error:
        raise DataExportError(f"Не вдалося записати {path}") from error


def export_errors(errors: Iterable[InvalidRecord], path: Path) -> int:
    """Write rejected rows with the error message to a separate CSV file."""
    count = 0
    try:
        with AtomicWriter(path) as file:
            writer = csv.DictWriter(file, fieldnames=["line", *FIELDS, "error"])
            writer.writeheader()
            for invalid in errors:
                values = {field: invalid.row.get(field, "") for field in FIELDS}
                writer.writerow({"line": invalid.line_number, **values, "error": invalid.error})
                count += 1
    except OSError as error:
        raise DataExportError(f"Не вдалося записати {path}") from error
    return count


def export_summary(summary: dict[str, object], path: Path) -> None:
    """Write the summary report of an import as JSON."""
    try:
        with AtomicWriter(path) as file:
            file.write(to_json(summary, indent=2) + "\n")
    except (OSError, TypeError) as error:
        raise DataExportError(f"Не вдалося записати {path}") from error
