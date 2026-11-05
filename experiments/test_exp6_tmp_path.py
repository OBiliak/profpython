"""Experiment 6: every run gets a new empty tmp_path and nothing is written to the project."""

import json
from pathlib import Path

from car_catalog.importer.exporters import export_records
from car_catalog.importer.models import VehicleRecord


def test_export_into_new_tmp_path(tmp_path: Path) -> None:
    print(f"\ntmp_path = {tmp_path}")
    assert list(tmp_path.iterdir()) == []

    export_records([VehicleRecord(5, "BMW", "X5", 2020, 1_890_000.0, 54_000)], tmp_path / "out.json")

    assert json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))[0]["model"] == "X5"
