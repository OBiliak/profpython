"""Experiments 1–2: average price with a deliberate bug (not part of the package)."""


def average_price_with_bug(prices: list[float]) -> float:
    """Return the average price; deliberate bug: divides by n + 1."""
    return sum(prices) / (len(prices) + 1)
