"""Experiment 3: a function with three branches (not part of the package)."""


def classify_price(price: float) -> str:
    """Return the price segment of a car."""
    if price >= 2_000_000:
        return "premium"
    if price >= 800_000:
        return "middle"
    return "budget"
