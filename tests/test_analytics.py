"""Unit tests for car record processors, analytics and decorators."""

import unittest

from car_catalog.analytics import (
    calculate_average_price,
    calculate_average_values,
    create_car_record,
    create_mileage_filter,
    create_price_filter,
    filter_cars,
    find_lowest_mileage_car,
    find_most_expensive_car,
    sort_by_price,
    sort_cars,
)
from car_catalog.decorators import operation_history
from car_catalog.processors import (
    count_cars_by_brand,
    create_car_index,
    filter_by_year,
    find_car_by_id,
    find_car_linear,
    get_unique_brands,
    group_by_brand,
    group_by_brand_and_year,
)


class CarAnalyticsTest(unittest.TestCase):
    """Tests for processing and analysis of car records."""

    def setUp(self) -> None:
        """Prepare a small list of car records."""
        self.cars = [
            {"id": 1, "brand": "Toyota", "model": "Corolla", "year": 2018, "price": 500000.0, "mileage": 80000},
            {"id": 2, "brand": "BMW", "model": "X3", "year": 2021, "price": 1500000.0, "mileage": 30000},
            {"id": 3, "brand": "Toyota", "model": "Yaris", "year": 2014, "price": 250000.0, "mileage": 120000},
        ]

    def test_gets_unique_brands(self) -> None:
        self.assertEqual(get_unique_brands(self.cars), {"Toyota", "BMW"})

    def test_counts_cars_by_brand(self) -> None:
        self.assertEqual(count_cars_by_brand(self.cars)["Toyota"], 2)

    def test_finds_car_in_index_by_id(self) -> None:
        index = create_car_index(self.cars)
        self.assertEqual(find_car_by_id(index, 2)["model"], "X3")

    def test_returns_none_for_unknown_id(self) -> None:
        index = create_car_index(self.cars)
        self.assertIsNone(find_car_by_id(index, 99))

    def test_linear_search_matches_index_search(self) -> None:
        index = create_car_index(self.cars)
        self.assertIs(find_car_linear(self.cars, 3), find_car_by_id(index, 3))

    def test_filters_by_year_range_including_bounds(self) -> None:
        result = filter_by_year(self.cars, 2014, 2018)
        self.assertEqual([car["id"] for car in result], [1, 3])

    def test_groups_by_brand(self) -> None:
        self.assertEqual(len(group_by_brand(self.cars)["Toyota"]), 2)

    def test_groups_by_brand_and_year(self) -> None:
        result = group_by_brand_and_year(self.cars)
        self.assertEqual(result["Toyota"], {2018: ["Corolla"], 2014: ["Yaris"]})

    def test_calculates_average_price(self) -> None:
        self.assertAlmostEqual(calculate_average_price(self.cars), 750000.0)

    def test_average_price_of_empty_catalog_is_zero(self) -> None:
        self.assertEqual(calculate_average_price([]), 0.0)

    def test_finds_most_expensive_car(self) -> None:
        self.assertEqual(find_most_expensive_car(self.cars)["model"], "X3")

    def test_finds_lowest_mileage_car(self) -> None:
        self.assertEqual(find_lowest_mileage_car(self.cars)["model"], "X3")

    def test_returns_none_for_empty_catalog(self) -> None:
        self.assertIsNone(find_most_expensive_car([]))

    def test_sorts_by_price(self) -> None:
        result = sort_by_price(self.cars)
        self.assertEqual([car["id"] for car in result], [3, 1, 2])

    def test_sorts_by_any_field_descending(self) -> None:
        result = sort_cars(self.cars, "mileage", reverse=True)
        self.assertEqual([car["id"] for car in result], [3, 1, 2])

    def test_calculates_average_of_args(self) -> None:
        self.assertEqual(calculate_average_values(10, 20, 30), 20)

    def test_creates_record_from_kwargs(self) -> None:
        record = create_car_record(id=4, brand="Audi")
        self.assertEqual(record, {"id": 4, "brand": "Audi"})

    def test_closure_filters_combine(self) -> None:
        result = filter_cars(self.cars, create_price_filter(600000), create_mileage_filter(100000))
        self.assertEqual([car["id"] for car in result], [1])

    def test_closure_remembers_limit(self) -> None:
        is_cheap = create_price_filter(300000)
        self.assertTrue(is_cheap(self.cars[2]))

    def test_logs_operations_in_history(self) -> None:
        operation_history.clear()
        filter_by_year(self.cars, 2020)
        self.assertEqual(operation_history[-1], ("фільтр за роком", 1))

    def test_history_keeps_last_five_operations(self) -> None:
        for _ in range(7):
            sort_by_price(self.cars)
        self.assertEqual(len(operation_history), 5)


if __name__ == "__main__":
    unittest.main()
