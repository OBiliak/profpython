"""Streaming importers of CSV, JSON Lines, JSON and YAML files behind one interface."""

import csv
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Protocol

import yaml

from car_catalog.importer.exceptions import DataImportError
from car_catalog.importer.files import open_input, retry

Row = dict[str, Any]
FIELDS = ("vehicle_id", "brand", "model", "year", "price", "mileage")


class Importer(Protocol):
    """Reads rows of an input file one by one with their line numbers."""

    def read(self, path: Path) -> Iterator[tuple[int, Row]]:
        """Yield (line_number, row) pairs."""
        ...


class CsvImporter:
    """Streaming CSV reader based on csv.DictReader."""

    def read(self, path: Path) -> Iterator[tuple[int, Row]]:
        """Yield CSV rows one by one."""
        try:
            with retry(lambda: open_input(path)) as file:
                reader = csv.DictReader(file)
                missing = set(FIELDS) - set(reader.fieldnames or [])
                if missing:
                    raise DataImportError(f"У заголовку CSV немає колонок: {sorted(missing)}")
                for row in reader:
                    yield reader.line_num, dict(row)
        except (OSError, UnicodeDecodeError, csv.Error) as error:
            raise DataImportError(f"Не вдалося прочитати файл {path}") from error


class JsonLinesImporter:
    """Streaming JSON Lines reader: one JSON object per line."""

    def read(self, path: Path) -> Iterator[tuple[int, Row]]:
        """Yield objects of a .jsonl file one by one."""
        try:
            with retry(lambda: open_input(path)) as file:
                for line_number, line in enumerate(file, start=1):
                    if line.strip():
                        yield line_number, json.loads(line)
        except json.JSONDecodeError as error:
            raise DataImportError(f"Некоректний JSON у рядку {error.lineno} файлу {path}") from error
        except (OSError, UnicodeDecodeError) as error:
            raise DataImportError(f"Не вдалося прочитати файл {path}") from error


def load_document(path: Path) -> object:
    """Load a whole JSON or YAML document (not streaming)."""
    try:
        with retry(lambda: open_input(path)) as file:
            if data_suffix(path) == ".json":
                return json.load(file)
            return yaml.safe_load(file)
    except (json.JSONDecodeError, yaml.YAMLError) as error:
        raise DataImportError(f"Некоректний документ {path}") from error
    except (OSError, UnicodeDecodeError) as error:
        raise DataImportError(f"Не вдалося прочитати файл {path}") from error


class DocumentImporter:
    """Reader of a JSON or YAML list of objects; the document is loaded entirely."""

    def read(self, path: Path) -> Iterator[tuple[int, Row]]:
        """Yield items of the list with their positions."""
        items = load_document(path)
        if not isinstance(items, list):
            raise DataImportError(f"Файл {path} має містити список записів.")
        for number, item in enumerate(items, start=1):
            yield number, item if isinstance(item, dict) else {}


IMPORTERS: dict[str, Importer] = {
    ".csv": CsvImporter(),
    ".jsonl": JsonLinesImporter(),
    ".json": DocumentImporter(),
    ".yaml": DocumentImporter(),
    ".yml": DocumentImporter(),
}


def data_suffix(path: Path) -> str:
    """Return the data format extension, ignoring .gz compression."""
    suffixes = [suffix for suffix in path.suffixes if suffix != ".gz"]
    return suffixes[-1].lower() if suffixes else ""


def select_importer(path: Path) -> Importer:
    """Choose the importer by the file extension."""
    try:
        return IMPORTERS[data_suffix(path)]
    except KeyError as error:
        raise DataImportError(f"Непідтримуваний формат вхідного файлу: {path.name}") from error
