"""Integration test of python -m car_catalog.api_demo: a real Uvicorn server and real HTTP requests."""

import socket
from pathlib import Path

import pytest

from car_catalog.api_demo import main

pytestmark = pytest.mark.integration


def free_port() -> int:
    """A TCP port that is free at the moment."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port: int = sock.getsockname()[1]
        return port


def test_main_runs_api_scenario(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = main([str(free_port())])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert (tmp_path / "car_catalog.db").exists()
    assert "POST /cars → 201 Created" in output
    assert "DELETE /cars/11 → 204 No Content" in output
    assert "POST /cars → 409 Conflict" in output
    assert "GET /cars/999 → 404 Not Found" in output
    assert (
        "Semaphore(3): 10 tasks, завантажено 10, помилок 0, одночасно виконувалось не більше 3"
        in output
    )
    assert "Результат після 3 спроб" in output
    assert "TimeoutError" in output


def test_main_reports_busy_port(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        port = busy.getsockname()[1]

        exit_code = main([str(port)])

    assert exit_code == 1
    assert "Сервер не запустився" in capsys.readouterr().out
