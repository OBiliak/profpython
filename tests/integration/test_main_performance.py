"""The performance demo of laboratory work 9 runs on a small catalog and checks its results."""

import pytest

from car_catalog.main import main


@pytest.mark.integration
def test_main_prints_all_parts(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["3000"]) == 0
    output = capsys.readouterr().out
    for heading in (
        "1. Baseline",
        "2. cProfile",
        "3. tracemalloc",
        "4. CPU-bound",
        "5. I/O-bound",
        "6. Race condition",
        "7. Caching",
    ):
        assert heading in output
    assert "Згенеровано 3000 автомобілів" in output
    assert "Bottleneck: residual_value() — 3000 викликів" in output
    assert output.count("однакові: True") == 4
    assert "однакові (rtol 1e-9): True" in output
    assert "з Lock: 8000000  правильно: True" in output
    assert "той самий об'єкт: True" in output
    assert "cache_clear(): (0, 0, 0)" in output
