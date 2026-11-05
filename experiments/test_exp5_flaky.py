"""Experiment 5: a flaky test that depends on randomness and its deterministic version."""

import random

from car_of_day import pick_car_of_day

MODELS = ["Corolla", "RAV4", "Octavia", "X5", "Model 3"]


def test_car_of_day_flaky() -> None:
    assert pick_car_of_day(MODELS) == "Corolla"


def test_car_of_day_deterministic() -> None:
    first = pick_car_of_day(MODELS, random.Random(5))
    second = pick_car_of_day(MODELS, random.Random(5))

    assert first == second
    assert first in MODELS
