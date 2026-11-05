"""Helper functions for numbers with a constrained TypeVar."""

from collections.abc import Sequence
from typing import TypeVar

Number = TypeVar("Number", int, float)


def smallest(values: Sequence[Number]) -> Number:
    """Return the smallest value; the result has the same type as the values."""
    if not values:
        raise ValueError("Послідовність порожня.")
    return min(values)


def largest(values: Sequence[Number]) -> Number:
    """Return the largest value; the result has the same type as the values."""
    if not values:
        raise ValueError("Послідовність порожня.")
    return max(values)


def average(values: Sequence[Number]) -> float:
    """Return the arithmetic mean of the values."""
    if not values:
        raise ValueError("Послідовність порожня.")
    return sum(values) / len(values)
