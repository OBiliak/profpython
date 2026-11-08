"""Unit tests of Vehicle/Car creation, field validation and value objects."""

from collections.abc import Callable

import pytest

from car_catalog.domain.exceptions import InvalidVehicleError
from car_catalog.domain.models import Car, ElectricCar
from car_catalog.domain.value_objects import Mileage, Money


def test_creates_car_with_valid_fields(make_car: Callable[..., Car]) -> None:
    car = make_car(1, "  Toyota ", "Corolla", 2018, 520_000, 85_000)

    assert car.id == 1
    assert car.brand == "Toyota"
    assert car.model == "Corolla"
    assert car.year == 2018
    assert car.price == Money(520_000)
    assert car.mileage == Mileage(85_000)
    assert car.kind() == "Автомобіль"


@pytest.mark.parametrize("year", [1950, 2026], ids=["min-year", "max-year"])
def test_accepts_boundary_year(make_car: Callable[..., Car], year: int) -> None:
    assert make_car(year=year).year == year


@pytest.mark.parametrize("year", [1949, 2027], ids=["below-min", "above-max"])
def test_rejects_year_outside_range(make_car: Callable[..., Car], year: int) -> None:
    with pytest.raises(InvalidVehicleError, match="Рік має бути від 1950 до 2026"):
        make_car(year=year)


@pytest.mark.parametrize(
    ("brand", "model"),
    [("", "Corolla"), ("Toyota", "   ")],
    ids=["empty-brand", "blank-model"],
)
def test_rejects_empty_brand_or_model(make_car: Callable[..., Car], brand: str, model: str) -> None:
    with pytest.raises(InvalidVehicleError, match="не можуть бути порожніми"):
        make_car(brand=brand, model=model)


def test_accepts_minimal_positive_price(make_car: Callable[..., Car]) -> None:
    assert make_car(price=0.01).price.amount == pytest.approx(0.01)


@pytest.mark.parametrize("price", [0, -1], ids=["zero", "negative"])
def test_rejects_not_positive_price(make_car: Callable[..., Car], price: float) -> None:
    with pytest.raises(InvalidVehicleError):
        make_car(price=price)


def test_accepts_zero_mileage(make_car: Callable[..., Car]) -> None:
    assert make_car(mileage=0).mileage.km == 0


def test_rejects_negative_mileage(make_car: Callable[..., Car]) -> None:
    with pytest.raises(InvalidVehicleError, match="Пробіг не може бути від'ємним"):
        make_car(mileage=-1)


def test_price_setter_keeps_old_price_after_error(make_car: Callable[..., Car]) -> None:
    car = make_car(price=520_000)

    with pytest.raises(InvalidVehicleError):
        car.price = Money(0)

    assert car.price == Money(520_000)


def test_rejects_electric_car_without_battery() -> None:
    with pytest.raises(InvalidVehicleError, match="батареї"):
        ElectricCar(6, "Tesla", "Model 3", 2022, Money(1_450_000), Mileage(28_000), 0, 500)


def test_money_rejects_different_currencies() -> None:
    with pytest.raises(InvalidVehicleError, match="Валюти не збігаються"):
        Money(100, "грн") + Money(100, "USD")


def test_money_division_gives_float_average() -> None:
    average = (Money(0.1) + Money(0.2)) / 3

    assert average.amount == pytest.approx(0.1)
