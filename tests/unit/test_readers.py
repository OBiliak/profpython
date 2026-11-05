"""Unit tests of input readers: CSV import, malformed files and unsupported formats."""

from collections.abc import Callable
from pathlib import Path

import pytest

from car_catalog.importer.exceptions import DataImportError
from car_catalog.importer.readers import CsvImporter, select_importer


def test_csv_importer_yields_rows_with_line_numbers(write_csv: Callable[..., Path]) -> None:
    path = write_csv("1,Toyota,Corolla,2018,520000,85000", "5,BMW,X5,2020,1890000,54000")

    rows = list(CsvImporter().read(path))

    assert [number for number, _ in rows] == [2, 3]
    assert rows[1][1]["brand"] == "BMW"


def test_csv_without_required_column(tmp_path: Path) -> None:
    path = tmp_path / "vehicles.csv"
    path.write_text(
        "vehicle_id,brand,model,year,price\n1,Toyota,Corolla,2018,520000\n", encoding="utf-8"
    )

    with pytest.raises(DataImportError, match="mileage"):
        list(CsvImporter().read(path))


def test_missing_input_file_error_is_chained(tmp_path: Path) -> None:
    with pytest.raises(DataImportError, match="Не вдалося прочитати") as exc_info:
        list(CsvImporter().read(tmp_path / "absent.csv"))

    assert isinstance(exc_info.value.__cause__, FileNotFoundError)


@pytest.mark.parametrize(
    ("name", "content", "message"),
    [
        ("broken.jsonl", '{"vehicle_id": 1}\n{broken\n', "Некоректний JSON у рядку 2"),
        ("broken.json", "[{", "Некоректний документ"),
        ("object.yaml", "vehicle_id: 1\n", "має містити список записів"),
    ],
    ids=["jsonl-broken-line", "json-broken-document", "yaml-not-list"],
)
def test_malformed_files_raise_import_error(
    tmp_path: Path, name: str, content: str, message: str
) -> None:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")

    with pytest.raises(DataImportError, match=message):
        list(select_importer(path).read(path))


def test_unsupported_input_format(tmp_path: Path) -> None:
    with pytest.raises(DataImportError, match="Непідтримуваний формат"):
        select_importer(tmp_path / "vehicles.xlsx")
