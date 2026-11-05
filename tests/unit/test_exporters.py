"""Unit tests of JSON export: tmp_path files, formats and atomic output."""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from car_catalog.importer.exceptions import DataExportError
from car_catalog.importer.exporters import export_records, to_json
from car_catalog.importer.models import VehicleRecord
from car_catalog.importer.readers import select_importer

RECORDS = [
    VehicleRecord(5, "BMW", "X5", 2020, 1_890_000.0, 54_000),
    VehicleRecord(6, "Tesla", "Model 3", 2022, 1_450_000.0, 28_000),
]


@pytest.fixture(params=[".json", ".jsonl"], ids=["json", "json-lines"])
def output_path(request: pytest.FixtureRequest, tmp_path: Path) -> Path:
    """Return an output path for every supported export format."""
    return tmp_path / f"vehicles{request.param}"


def test_exports_records_to_json_file(tmp_path: Path) -> None:
    path = tmp_path / "vehicles.json"

    count = export_records(RECORDS, path)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert count == 2
    assert data[0] == {
        "vehicle_id": 5,
        "brand": "BMW",
        "model": "X5",
        "year": 2020,
        "price": 1_890_000.0,
        "mileage": 54_000,
    }
    assert data[1]["price"] == pytest.approx(1_450_000)


def test_exported_file_can_be_imported_back(output_path: Path) -> None:
    export_records(RECORDS, output_path)

    rows = [row for _, row in select_importer(output_path).read(output_path)]

    assert [row["model"] for row in rows] == ["X5", "Model 3"]


def test_exports_empty_catalog_as_empty_list(tmp_path: Path) -> None:
    path = tmp_path / "empty.json"

    assert export_records([], path) == 0
    assert json.loads(path.read_text(encoding="utf-8")) == []


def test_rejects_unsupported_output_format(tmp_path: Path) -> None:
    with pytest.raises(DataExportError, match="Непідтримуваний формат"):
        export_records(RECORDS, tmp_path / "vehicles.xml")


def broken_records() -> Iterator[VehicleRecord]:
    """Yield one record and then fail like a broken data source."""
    yield RECORDS[0]
    raise OSError("диск недоступний")


def test_failed_export_keeps_previous_file(tmp_path: Path) -> None:
    path = tmp_path / "vehicles.json"
    export_records(RECORDS, path)
    previous = path.read_text(encoding="utf-8")

    with pytest.raises(DataExportError) as exc_info:
        export_records(broken_records(), path)

    assert path.read_text(encoding="utf-8") == previous
    assert not (tmp_path / "vehicles.json.tmp").exists()
    assert isinstance(exc_info.value.__cause__, OSError)


def test_export_with_backup_keeps_old_version(tmp_path: Path) -> None:
    path = tmp_path / "vehicles.json"
    export_records(RECORDS[:1], path)

    export_records(RECORDS, path, backup=True)

    assert len(json.loads((tmp_path / "vehicles.json.bak").read_text(encoding="utf-8"))) == 1
    assert len(json.loads(path.read_text(encoding="utf-8"))) == 2


def test_json_encoder_rejects_unknown_object() -> None:
    with pytest.raises(TypeError):
        to_json({"vehicle": object()})
