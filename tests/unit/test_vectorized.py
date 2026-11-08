"""Tests: the NumPy implementation gives the same results as the Python loops."""

import numpy as np
import pytest

from car_catalog.performance import analytics, vectorized
from car_catalog.performance.analytics import CarRecord, generate_cars


@pytest.fixture(scope="module")
def cars() -> list[CarRecord]:
    return generate_cars(5_000, seed=7)


@pytest.fixture(scope="module")
def arrays(cars: list[CarRecord]) -> vectorized.CatalogArrays:
    return vectorized.to_arrays(cars)


def test_arrays_have_compact_dtypes(arrays: vectorized.CatalogArrays) -> None:
    assert arrays.brand_codes.dtype == np.int8
    assert arrays.years.dtype == np.int16
    assert len(arrays.prices) == 5_000
    assert arrays.nbytes == 5_000 * (4 + 1 + 2 + 8 + 4)


@pytest.mark.parametrize("brand", ["Toyota", "BMW", "Tesla"])
def test_count_by_brand(
    cars: list[CarRecord], arrays: vectorized.CatalogArrays, brand: str
) -> None:
    assert vectorized.count_by_brand(arrays, brand) == len(analytics.find_by_brand(cars, brand))


@pytest.mark.parametrize(("min_year", "max_year"), [(2019, 2022), (1995, 1995), (2027, 2030)])
def test_count_by_years(
    cars: list[CarRecord], arrays: vectorized.CatalogArrays, min_year: int, max_year: int
) -> None:
    expected = len(analytics.filter_by_year(cars, min_year, max_year))
    assert vectorized.count_by_years(arrays, min_year, max_year) == expected


def test_extreme_cars_and_average(cars: list[CarRecord], arrays: vectorized.CatalogArrays) -> None:
    assert vectorized.most_expensive_id(arrays) == analytics.most_expensive(cars).car_id
    assert vectorized.lowest_mileage_id(arrays) == analytics.lowest_mileage(cars).car_id
    assert vectorized.average_price(arrays) == pytest.approx(analytics.average_price(cars))


def test_mileage_statistics(cars: list[CarRecord], arrays: vectorized.CatalogArrays) -> None:
    expected = analytics.mileage_statistics(cars)
    result = vectorized.mileage_statistics(arrays)
    assert (result.minimum, result.maximum) == (expected.minimum, expected.maximum)
    assert result.average == pytest.approx(expected.average)
    assert result.std == pytest.approx(expected.std)


def test_manufacturer_statistics(cars: list[CarRecord], arrays: vectorized.CatalogArrays) -> None:
    expected = analytics.manufacturer_statistics(cars)
    result = vectorized.manufacturer_statistics(arrays)
    assert list(result) == list(expected)
    for brand, statistics in expected.items():
        assert result[brand].count == statistics.count
        assert result[brand].average_price == pytest.approx(statistics.average_price)
        assert result[brand].average_mileage == pytest.approx(statistics.average_mileage)
        assert result[brand].max_price == statistics.max_price


def test_missing_brand_is_not_in_statistics() -> None:
    arrays = vectorized.to_arrays([CarRecord(1, "BMW", "X5", 2020, 1_000_000.0, 10_000)])
    assert list(vectorized.manufacturer_statistics(arrays)) == ["BMW"]


def test_residual_values_match_python_loop(
    cars: list[CarRecord], arrays: vectorized.CatalogArrays
) -> None:
    expected = analytics.residual_values_sequential(cars)
    assert vectorized.residual_values(arrays) == pytest.approx(expected, rel=1e-9)


def test_residual_value_is_never_negative() -> None:
    car = CarRecord(1, "Renault", "Logan", 1995, 1_000.0, 578_000)
    assert analytics.car_residual_value(car) == 0.0
    assert vectorized.residual_values(vectorized.to_arrays([car]))[0] == 0.0


def test_catalog_reports_are_the_same(
    cars: list[CarRecord], arrays: vectorized.CatalogArrays
) -> None:
    expected = analytics.catalog_report(cars)
    result = vectorized.catalog_report(arrays)
    assert result["toyota"] == expected["toyota"]
    assert result["years_2019_2022"] == expected["years_2019_2022"]
    assert result["most_expensive"] == expected["most_expensive"].car_id  # type: ignore[attr-defined]
    assert result["average_residual"] == pytest.approx(expected["average_residual"])
