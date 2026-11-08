"""Unit tests of the import/export module (laboratory work 5)."""

import io
import json
import logging
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path

import yaml

from car_catalog.importer.config import load_config
from car_catalog.importer.exceptions import (
    ConfigurationError,
    DataExportError,
    DataImportError,
    RecordValidationError,
)
from car_catalog.importer.exporters import export_errors, export_records, to_json
from car_catalog.importer.files import AtomicWriter, backup_path, retry
from car_catalog.importer.logging_config import configure_logging
from car_catalog.importer.models import InvalidRecord, LoggingConfig, VehicleRecord
from car_catalog.importer.readers import select_importer
from car_catalog.importer.services import ImportStatistics, filter_by_price, import_vehicles
from car_catalog.importer.validators import ValidationPolicy

HEADER = "vehicle_id,brand,model,year,price,mileage\n"


def make_row(**changes: str) -> dict[str, str]:
    """Return a valid raw row with optional changed fields."""
    row = {
        "vehicle_id": "1",
        "brand": "Toyota",
        "model": "Corolla",
        "year": "2018",
        "price": "520000",
        "mileage": "85000",
    }
    row.update(changes)
    return row


class TestValidationPolicy(unittest.TestCase):
    """Parsing and validation of single records."""

    def setUp(self) -> None:
        self.policy = ValidationPolicy(1950, 2026)

    def test_parses_valid_row(self) -> None:
        record = self.policy.parse(make_row(), 2)
        self.assertEqual(record, VehicleRecord(1, "Toyota", "Corolla", 2018, 520000.0, 85000))

    def test_rejects_non_positive_id(self) -> None:
        with self.assertRaises(RecordValidationError) as context:
            self.policy.parse(make_row(vehicle_id="0"), 3)
        self.assertEqual(context.exception.field, "vehicle_id")

    def test_rejects_empty_brand(self) -> None:
        with self.assertRaises(RecordValidationError):
            self.policy.parse(make_row(brand="  "), 2)

    def test_rejects_year_outside_range(self) -> None:
        with self.assertRaises(RecordValidationError) as context:
            self.policy.parse(make_row(year="1935"), 5)
        self.assertEqual(context.exception.line_number, 5)

    def test_rejects_negative_price_and_mileage(self) -> None:
        for field in ("price", "mileage"):
            with self.assertRaises(RecordValidationError):
                self.policy.parse(make_row(**{field: "-1"}), 2)

    def test_keeps_value_error_as_cause(self) -> None:
        with self.assertRaises(RecordValidationError) as context:
            self.policy.parse(make_row(year="wrong"), 2)
        self.assertIsInstance(context.exception.__cause__, ValueError)


class TestImportService(unittest.TestCase):
    """Strict and tolerant processing, filtering and statistics."""

    def setUp(self) -> None:
        self.policy = ValidationPolicy(1950, 2026)
        self.rows = [
            (2, make_row()),
            (3, make_row(vehicle_id="abc")),
            (4, make_row(vehicle_id="3", price="4200000")),
        ]
        logging.disable(logging.CRITICAL)

    def tearDown(self) -> None:
        logging.disable(logging.NOTSET)

    def test_tolerant_mode_skips_invalid_records(self) -> None:
        statistics, errors = ImportStatistics(), []
        vehicles = list(
            import_vehicles(
                self.rows,
                policy=self.policy,
                skip_invalid=True,
                statistics=statistics,
                errors=errors,
            )
        )
        self.assertEqual([vehicle.vehicle_id for vehicle in vehicles], [1, 3])
        self.assertEqual((statistics.total, statistics.valid, statistics.invalid), (3, 2, 1))
        self.assertEqual(errors[0].line_number, 3)

    def test_strict_mode_stops_on_first_invalid_record(self) -> None:
        vehicles = import_vehicles(
            self.rows,
            policy=self.policy,
            skip_invalid=False,
            statistics=ImportStatistics(),
            errors=[],
        )
        with self.assertRaises(RecordValidationError):
            list(vehicles)

    def test_filters_by_price_range(self) -> None:
        statistics = ImportStatistics()
        vehicles = import_vehicles(
            self.rows, policy=self.policy, skip_invalid=True, statistics=statistics, errors=[]
        )
        selected = list(filter_by_price(vehicles, 0, 2_000_000, statistics))
        self.assertEqual(len(selected), 1)
        self.assertEqual(statistics.filtered, 1)


class TestFiles(unittest.TestCase):
    """Readers, exporters, atomic writer, retry, encoder and logging."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.vehicles = [
            VehicleRecord(1, "Toyota", "Corolla", 2018, 520000.0, 85000),
            VehicleRecord(2, "Škoda", "Octavia", 2019, 610000.0, 67000),
        ]
        logging.disable(logging.CRITICAL)

    def tearDown(self) -> None:
        logging.disable(logging.NOTSET)
        logging.basicConfig(force=True)
        self.temp.cleanup()

    def test_reads_csv_rows_with_line_numbers(self) -> None:
        path = self.root / "cars.csv"
        path.write_text(HEADER + "1,Toyota,Corolla,2018,520000,85000\n", encoding="utf-8")
        rows = list(select_importer(path).read(path))
        self.assertEqual(rows[0][0], 2)
        self.assertEqual(rows[0][1]["brand"], "Toyota")

    def test_rejects_csv_without_required_columns(self) -> None:
        path = self.root / "cars.csv"
        path.write_text("id,brand\n1,Toyota\n", encoding="utf-8")
        with self.assertRaises(DataImportError):
            list(select_importer(path).read(path))

    def test_missing_input_file_raises_import_error_with_cause(self) -> None:
        path = self.root / "missing.csv"
        with self.assertRaises(DataImportError) as context:
            list(select_importer(path).read(path))
        self.assertIsInstance(context.exception.__cause__, FileNotFoundError)

    def test_rejects_unknown_extension(self) -> None:
        with self.assertRaises(DataImportError):
            select_importer(self.root / "cars.xlsx")

    def test_round_trip_in_all_output_formats(self) -> None:
        for name in ("cars.json", "cars.jsonl", "cars.json.gz", "cars.jsonl.gz"):
            path = self.root / name
            self.assertEqual(export_records(self.vehicles, path), 2)
            rows = [row for _, row in select_importer(path).read(path)]
            self.assertEqual(rows[1]["brand"], "Škoda", name)

    def test_reads_yaml_list(self) -> None:
        path = self.root / "cars.yaml"
        path.write_text(
            yaml.safe_dump([vehicle.to_dict() for vehicle in self.vehicles]), encoding="utf-8"
        )
        self.assertEqual(len(list(select_importer(path).read(path))), 2)

    def test_atomic_writer_keeps_previous_output_on_error(self) -> None:
        path = self.root / "cars.json"
        path.write_text("old", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            with AtomicWriter(path) as file:
                file.write("new")
                raise RuntimeError("export failed")
        self.assertEqual(path.read_text(encoding="utf-8"), "old")
        self.assertFalse((self.root / "cars.json.tmp").exists())

    def test_atomic_writer_creates_backup(self) -> None:
        path = self.root / "cars.json"
        path.write_text("old", encoding="utf-8")
        with AtomicWriter(path, backup=True) as file:
            file.write("new")
        self.assertEqual(backup_path(path).read_text(encoding="utf-8"), "old")
        self.assertEqual(path.read_text(encoding="utf-8"), "new")

    def test_export_to_directory_raises_export_error(self) -> None:
        path = self.root / "cars.json"
        path.mkdir()
        with self.assertRaises(DataExportError) as context:
            export_records(self.vehicles, path)
        self.assertIsInstance(context.exception.__cause__, OSError)

    def test_writes_error_csv(self) -> None:
        path = self.root / "invalid.csv"
        count = export_errors([InvalidRecord(3, make_row(vehicle_id="abc"), "bad id")], path)
        self.assertEqual(count, 1)
        self.assertIn("3,abc,Toyota", path.read_text(encoding="utf-8"))

    def test_retry_repeats_after_permission_error(self) -> None:
        calls: list[int] = []

        def unstable() -> str:
            calls.append(1)
            if len(calls) < 3:
                raise PermissionError("file is locked")
            return "ok"

        self.assertEqual(retry(unstable, attempts=3, delay=0), "ok")
        self.assertEqual(len(calls), 3)

    def test_retry_raises_after_last_attempt(self) -> None:
        def locked() -> str:
            raise PermissionError("file is locked")

        with self.assertRaises(PermissionError):
            retry(locked, attempts=2, delay=0)

    def test_custom_encoder_serializes_path_datetime_and_dataclass(self) -> None:
        text = to_json(
            {
                "path": Path("data/cars.csv"),
                "at": datetime(2026, 11, 6, 12, 0),
                "car": self.vehicles[0],
            }
        )
        data = json.loads(text)
        self.assertEqual(data["path"], "data/cars.csv")
        self.assertEqual(data["at"], "2026-11-06T12:00:00")
        self.assertEqual(data["car"]["vehicle_id"], 1)

    def test_rotates_log_file(self) -> None:
        logging.disable(logging.NOTSET)
        log_path = self.root / "logs" / "app.log"
        logger = logging.getLogger("car_catalog.test")
        with redirect_stdout(io.StringIO()):
            configure_logging(LoggingConfig("INFO", log_path, max_bytes=200, backup_count=2))
            for number in range(20):
                logger.info("record %s", number)
        self.assertTrue(log_path.with_name("app.log.1").exists())


class TestConfiguration(unittest.TestCase):
    """Loading and validation of config.yaml."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "cars.csv").write_text(HEADER, encoding="utf-8")
        self.raw: dict[str, object] = {
            "schema_version": 1,
            "input": {"path": "cars.csv"},
            "output": {
                "path": "out/cars.json",
                "errors_path": "out/invalid.csv",
                "summary_path": "out/summary.json",
                "backup": True,
            },
            "validation": {"years": {"min": 1950, "max": 2026}},
            "filter": {"price": {"min": 0, "max": 2000000}},
            "processing": {"skip_invalid": True, "progress_every": 5},
            "logging": {"level": "INFO", "path": "logs/app.log"},
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, raw: dict[str, object]) -> Path:
        path = self.root / "config.yaml"
        path.write_text(yaml.safe_dump(raw), encoding="utf-8")
        return path

    def test_loads_nested_configuration(self) -> None:
        config = load_config(self.write(self.raw), {})
        self.assertEqual(config.validation.max_year, 2026)
        self.assertEqual(config.filter.max_price, 2_000_000)
        self.assertEqual(config.input.path, self.root / "cars.csv")

    def test_environment_variable_overrides_yaml(self) -> None:
        config = load_config(self.write(self.raw), {"CAR_IMPORT_SKIP_INVALID": "false"})
        self.assertFalse(config.processing.skip_invalid)

    def test_missing_file_raises_configuration_error(self) -> None:
        with self.assertRaises(ConfigurationError) as context:
            load_config(self.root / "missing.yaml", {})
        self.assertIsInstance(context.exception.__cause__, FileNotFoundError)

    def test_invalid_yaml_raises_configuration_error(self) -> None:
        path = self.root / "config.yaml"
        path.write_text("input: [cars.csv\n", encoding="utf-8")
        with self.assertRaises(ConfigurationError):
            load_config(path, {})

    def test_missing_key_raises_configuration_error(self) -> None:
        del self.raw["input"]
        with self.assertRaises(ConfigurationError):
            load_config(self.write(self.raw), {})

    def test_rejects_wrong_year_range(self) -> None:
        self.raw["validation"] = {"years": {"min": 2030, "max": 2026}}
        with self.assertRaises(ConfigurationError):
            load_config(self.write(self.raw), {})

    def test_rejects_unsupported_schema_version(self) -> None:
        self.raw["schema_version"] = 2
        with self.assertRaises(ConfigurationError):
            load_config(self.write(self.raw), {})


if __name__ == "__main__":
    unittest.main()
