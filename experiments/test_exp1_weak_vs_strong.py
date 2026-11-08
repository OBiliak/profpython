"""Experiments 1–2: weak vs strong tests, coverage without assertions."""

import pytest
from buggy_average import average_price_with_bug

PRICES = [520_000, 1_150_000, 610_000, 1_890_000, 1_450_000]


def test_average_weak() -> None:
    average_price_with_bug(PRICES)


def test_average_strong() -> None:
    assert average_price_with_bug(PRICES) == pytest.approx(1_124_000)
