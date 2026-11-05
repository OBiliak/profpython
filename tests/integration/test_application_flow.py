"""Integration tests of the entry points: configuration → import → statistics → export."""

import json
from pathlib import Path

import pytest

from car_catalog.importer import app
from car_catalog.main import main

pytestmark = pytest.mark.integration


def test_main_runs_catalog_scenario(config_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([str(config_file)])

    output = capsys.readouterr().out
    exported_path = config_file.parent / "output" / "catalog_2019_2022.json"
    exported = json.loads(exported_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert "усього 4, valid 3, invalid 1 (рядки 4)" in output
    assert "Найдорожчий: Автомобіль BMW X5" in output
    assert "пропущено: Не вдалося отримати довідку для ID 17" in output
    assert "Peugeot 308: Не вдалося отримати довідку для ID 17" in output
    assert [item["vehicle_id"] for item in exported] == [5, 17]


def test_main_reports_missing_configuration(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([str(tmp_path / "absent.yaml")]) == 1
    assert "Помилка: Файл конфігурації не знайдено" in capsys.readouterr().out


def test_import_application_writes_all_output_files(
    config_file: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("CAR_IMPORT_SKIP_INVALID", raising=False)

    assert app.main([str(config_file)]) == 0

    output = config_file.parent / "output"
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["statistics"]["exported"] == 3
    assert summary["invalid_lines"] == [4]
    assert (config_file.parent / "logs" / "test.log").exists()
    assert "демонстрацію YAML пропущено" in capsys.readouterr().out


def test_strict_mode_from_environment_keeps_output_unchanged(
    config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CAR_IMPORT_SKIP_INVALID", "false")

    assert app.main([str(config_file)]) == 1
    assert not (config_file.parent / "output" / "vehicles.json").exists()


def test_import_application_returns_2_for_invalid_configuration(tmp_path: Path) -> None:
    assert app.main([str(tmp_path / "absent.yaml")]) == 2


def test_import_application_reads_extra_yaml(
    config_file: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("CAR_IMPORT_SKIP_INVALID", raising=False)
    (config_file.parent / "vehicles_extra.yaml").write_text(
        "- {vehicle_id: 21, brand: Toyota, model: Camry, year: 2022, price: 1300000, mileage: 15000}\n"
        "- {vehicle_id: 22, brand: Kia, model: Rio, year: 1900, price: 400000, mileage: 90000}\n",
        encoding="utf-8",
    )

    assert app.main([str(config_file)]) == 0

    output = capsys.readouterr().out
    assert "21: Toyota Camry, 2022, 1300000 грн" in output
    assert "valid=1, invalid=1" in output
