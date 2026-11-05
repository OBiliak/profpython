"""Experiment 3: branch coverage of classify_price."""

import pytest

from price_segments import classify_price


@pytest.mark.parametrize(
    ("price", "segment"),
    [(4_200_000, "premium"), (1_150_000, "middle")],
)
def test_classify_first_two_branches(price: float, segment: str) -> None:
    assert classify_price(price) == segment


def test_classify_budget_branch() -> None:
    assert classify_price(520_000) == "budget"
