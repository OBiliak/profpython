"""Unit tests for the car catalog business logic."""

import unittest

from car_catalog.models import Car
from car_catalog.services import (
    EmptyCatalogError,
    add_car,
    calculate_average_price,
    filter_cars_by_year,
    find_cars_by_brand,
    find_lowest_mileage_car,
    find_most_expensive_car,
    search_cars,
    sort_cars_by_price,
)


class CarCatalogServicesTest(unittest.TestCase):
    """Tests for search, filtering and statistics of the car catalog."""

    def setUp(self) -> None:
        """Prepare a small catalog of cars."""
        self.cars = [
            Car("Toyota", "Corolla", 2018, 500000.0, 80000),
            Car("BMW", "X3", 2021, 1500000.0, 30000),
            Car("Toyota", "Yaris", 2014, 250000.0, 120000),
        ]

    def test_adds_car(self) -> None:
        add_car(self.cars, Car("Skoda", "Fabia", 2016, 300000.0, 90000))
        self.assertEqual(len(self.cars), 4)

    def test_finds_cars_by_brand_ignoring_case(self) -> None:
        result = find_cars_by_brand(self.cars, "toyota")
        self.assertEqual([car.model for car in result], ["Corolla", "Yaris"])

    def test_returns_empty_list_for_unknown_brand(self) -> None:
        self.assertEqual(find_cars_by_brand(self.cars, "Audi"), [])

    def test_filters_cars_by_min_year(self) -> None:
        result = filter_cars_by_year(self.cars, 2018)
        self.assertEqual([car.model for car in result], ["Corolla", "X3"])

    def test_filters_cars_by_year_range_including_bounds(self) -> None:
        result = filter_cars_by_year(self.cars, 2014, 2018)
        self.assertEqual([car.model for car in result], ["Corolla", "Yaris"])

    def test_finds_most_expensive_car(self) -> None:
        self.assertEqual(find_most_expensive_car(self.cars).model, "X3")

    def test_most_expensive_of_empty_catalog_is_none(self) -> None:
        self.assertIsNone(find_most_expensive_car([]))

    def test_calculates_average_price(self) -> None:
        self.assertAlmostEqual(calculate_average_price(self.cars), 750000.0)

    def test_rejects_average_price_of_empty_catalog(self) -> None:
        with self.assertRaises(EmptyCatalogError):
            calculate_average_price([])

    def test_finds_lowest_mileage_car(self) -> None:
        self.assertEqual(find_lowest_mileage_car(self.cars).model, "X3")

    def test_searches_by_several_criteria(self) -> None:
        result = search_cars(self.cars, "Toyota", min_year=2015, max_price=600000)
        self.assertEqual([car.model for car in result], ["Corolla"])

    def test_sorts_cars_by_price(self) -> None:
        result = sort_cars_by_price(self.cars)
        self.assertEqual([car.model for car in result], ["Yaris", "Corolla", "X3"])

    def test_rejects_year_out_of_range(self) -> None:
        with self.assertRaises(ValueError):
            Car("Audi", "A4", 1900, 100000.0, 10)

    def test_rejects_negative_mileage(self) -> None:
        with self.assertRaises(ValueError):
            Car("Audi", "A4", 2010, 100000.0, -1)


if __name__ == "__main__":
    unittest.main()
