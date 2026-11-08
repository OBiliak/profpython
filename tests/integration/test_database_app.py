"""Integration test of the entry point of laboratory work 7 (python -m car_catalog.main)."""

from pathlib import Path

import pytest

from car_catalog.main import main

pytestmark = pytest.mark.integration


def test_main_creates_database_and_runs_scenario(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    main()
    main()  # the second run recreates the database and gives the same result

    output = capsys.readouterr().out
    assert (tmp_path / "car_catalog.db").exists()
    assert output.count("ревізія: 0002") == 2
    assert "Пошук за маркою «Toyota»: 3" in output
    assert "Середня ціна: 758000.00 грн" in output
    assert "Параметр \"Toyota' OR '1'='1\": 0 рядк." in output
    assert "після rollback: [380000.0, 640000.0]" in output
    assert "UNIQUE constraint failed: cars.vin" in output
    assert "Кількість автомобілів після відхилених записів: 10" in output
