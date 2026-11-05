"""Unit tests of retry logic, deterministic time and context manager cleanup."""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from car_catalog.importer import files, services
from car_catalog.importer.config import load_config
from car_catalog.importer.files import AtomicWriter, retry
from car_catalog.importer.services import ImportStatistics, build_summary
from car_catalog.importer.validators import ValidationPolicy


def test_retry_repeats_after_permission_error(monkeypatch: pytest.MonkeyPatch) -> None:
    sleep = Mock()
    monkeypatch.setattr(files.time, "sleep", sleep)
    action = Mock(side_effect=[PermissionError("файл зайнятий"), "відкрито"])

    assert retry(action, attempts=3, delay=0.5) == "відкрито"
    assert action.call_count == 2
    sleep.assert_called_once_with(0.5)


def test_retry_raises_after_last_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(files.time, "sleep", Mock())
    action = Mock(side_effect=PermissionError("файл зайнятий"))

    with pytest.raises(PermissionError):
        retry(action, attempts=2)

    assert action.call_count == 2


def test_retry_does_not_repeat_other_errors() -> None:
    action = Mock(side_effect=FileNotFoundError("немає файлу"))

    with pytest.raises(FileNotFoundError):
        retry(action)

    action.assert_called_once_with()


class FixedDatetime(datetime):
    """datetime with a fixed now() for deterministic tests."""

    @classmethod
    def now(cls, tz=None) -> "FixedDatetime":
        return cls(2026, 11, 6, 12, 0, 0)


def test_summary_uses_deterministic_time(
    config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(services, "datetime", FixedDatetime)
    config = load_config(config_file, environ={})

    summary = build_summary(config, ImportStatistics(total=4, valid=3, invalid=1), [])

    assert summary["created_at"] == datetime(2026, 11, 6, 12, 0, 0)
    assert summary["mode"] == "tolerant"


def test_atomic_writer_removes_temporary_file_on_error(tmp_path: Path) -> None:
    path = tmp_path / "vehicles.json"

    with pytest.raises(RuntimeError):
        with AtomicWriter(path) as file:
            file.write("[")
            raise RuntimeError("перервано")

    assert not path.exists()
    assert list(tmp_path.iterdir()) == []


def test_retry_with_zero_attempts_is_rejected() -> None:
    action = Mock()

    with pytest.raises(ValueError, match="attempts"):
        retry(action, attempts=0)

    action.assert_not_called()


def test_backup_is_not_created_for_new_file(tmp_path: Path) -> None:
    path = tmp_path / "vehicles.json"

    with AtomicWriter(path, backup=True) as file:
        file.write("[]")

    assert path.read_text(encoding="utf-8") == "[]"
    assert not (tmp_path / "vehicles.json.bak").exists()


def test_import_logs_progress(policy: ValidationPolicy, caplog: pytest.LogCaptureFixture) -> None:
    row = {"vehicle_id": "5", "brand": "BMW", "model": "X5", "year": "2020",
           "price": "1890000", "mileage": "54000"}
    rows = [(number, row) for number in range(1, 6)]

    with caplog.at_level("INFO"):
        vehicles = list(
            services.import_vehicles(
                rows,
                policy=policy,
                skip_invalid=True,
                statistics=ImportStatistics(),
                errors=[],
                progress_every=2,
            )
        )

    assert len(vehicles) == 5
    assert "Прогрес: оброблено 2, valid=2, invalid=0" in caplog.text
    assert "Прогрес: оброблено 4, valid=4, invalid=0" in caplog.text
