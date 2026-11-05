"""Experiment 5: a random choice that makes tests flaky (not part of the package)."""

import random


def pick_car_of_day(models: list[str], chooser: random.Random | None = None) -> str:
    """Return a random model; a seeded Random can be passed for repeatable results."""
    return (chooser or random).choice(models)
