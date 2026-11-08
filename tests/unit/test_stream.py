"""Unit tests for the streaming car pipeline."""

import tempfile
import unittest
from collections import Counter
from itertools import islice
from pathlib import Path

from car_catalog.stream.analytics import (
    calculate_statistics,
    count_by_brand_sorted,
    find_first,
    running_average_prices,
    take_first_n,
)
from car_catalog.stream.batches import batched_cars
from car_catalog.stream.filters import filter_by_brand, filter_by_year, parse_car, validate_cars
from car_catalog.stream.generate import generate_rows
from car_catalog.stream.iterators import CarIdRange, generate_ids
from car_catalog.stream.models import CarRecord
from car_catalog.stream.parsers import clean_lines, parse_csv_rows
from car_catalog.stream.pipeline import build_pipeline
from car_catalog.stream.readers import read_lines
from car_catalog.stream.transformations import normalize_cars

CSV_TEXT = """id,brand,model,year,price,mileage
1,Toyota,Corolla,2018,500000,80000

2,bmw,X3,2021,1500000,30000
3,Toyota,Yaris,2014,250000,120000
4,Ford,Focus,abc,300000,90000
"""


class StreamPipelineTest(unittest.TestCase):
    """Tests for iterators, generator stages and streaming analytics."""

    def setUp(self) -> None:
        """Write a small CSV file with one empty line and one invalid row."""
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "cars.csv"
        self.path.write_text(CSV_TEXT, encoding="utf-8")
        self.cars = [
            CarRecord(1, "Toyota", "Corolla", 2018, 500000.0, 80000),
            CarRecord(2, "BMW", "X3", 2021, 1500000.0, 30000),
            CarRecord(3, "Toyota", "Yaris", 2014, 250000.0, 120000),
        ]

    def tearDown(self) -> None:
        """Remove the temporary directory."""
        self.directory.cleanup()

    def test_custom_iterator_stops(self) -> None:
        self.assertEqual(list(CarIdRange(1, 3)), [1, 2, 3])

    def test_custom_iterator_is_one_shot(self) -> None:
        ids = CarIdRange(1, 2)
        list(ids)
        self.assertEqual(list(ids), [])

    def test_infinite_generator_with_islice(self) -> None:
        self.assertEqual(list(islice(generate_ids(10), 3)), [10, 11, 12])

    def test_reads_lines_lazily(self) -> None:
        lines = read_lines(self.path)
        self.assertEqual(next(lines).strip(), "id,brand,model,year,price,mileage")

    def test_cleans_empty_lines(self) -> None:
        self.assertEqual(list(clean_lines(["a\n", "  \n", " b "])), ["a", "b"])

    def test_parser_skips_header(self) -> None:
        rows = list(parse_csv_rows(["id,brand,model,year,price,mileage", "1,A,B,2020,1,2"]))
        self.assertEqual(rows, [["1", "A", "B", "2020", "1", "2"]])

    def test_rejects_invalid_row(self) -> None:
        with self.assertRaises(ValueError):
            parse_car(["4", "Ford", "Focus", "abc", "300000", "90000"])

    def test_counts_invalid_rows(self) -> None:
        stats = Counter()
        list(validate_cars([["1", "A", "B", "2020", "1", "2"], ["x"]], stats))
        self.assertEqual(stats, Counter(valid=1, invalid=1))

    def test_filters_by_brand_ignoring_case(self) -> None:
        result = list(filter_by_brand(self.cars, {"toyota"}))
        self.assertEqual([car.id for car in result], [1, 3])

    def test_filters_by_year_including_bounds(self) -> None:
        result = list(filter_by_year(self.cars, 2014, 2018))
        self.assertEqual([car.id for car in result], [1, 3])

    def test_normalizes_brand(self) -> None:
        car = CarRecord(1, "skoda", "Fabia", 2016, 1.0, 1)
        self.assertEqual(next(normalize_cars([car])).brand, "Skoda")

    def test_pipeline_from_file(self) -> None:
        stats = Counter()
        cars = list(build_pipeline([self.path], stats))
        self.assertEqual(([car.id for car in cars], stats["invalid"]), ([1, 2, 3], 1))

    def test_pipeline_is_lazy_until_iterated(self) -> None:
        stats = Counter()
        build_pipeline([self.path], stats)
        self.assertEqual(stats, Counter())

    def test_exhausted_generator_gives_nothing(self) -> None:
        cars = build_pipeline([self.path], Counter())
        list(cars)
        self.assertEqual(list(cars), [])

    def test_calculates_statistics(self) -> None:
        stats = calculate_statistics(self.cars)
        self.assertEqual(
            (stats["count"], stats["most_expensive"].id, stats["lowest_mileage"].id), (3, 2, 2)
        )
        self.assertAlmostEqual(stats["average_price"], 750000.0)

    def test_statistics_of_empty_stream(self) -> None:
        stats = calculate_statistics([])
        self.assertEqual(
            (stats["count"], stats["average_price"], stats["most_expensive"]), (0, 0.0, None)
        )

    def test_running_average(self) -> None:
        self.assertEqual(list(running_average_prices(self.cars)), [500000.0, 1000000.0, 750000.0])

    def test_find_first_stops_early(self) -> None:
        stream = iter(self.cars)
        find_first(stream, lambda car: car.brand == "BMW")
        self.assertEqual(next(stream).id, 3)

    def test_take_first_n(self) -> None:
        result = take_first_n(self.cars, lambda car: car.price < 1_000_000, 1)
        self.assertEqual([car.id for car in result], [1])

    def test_batches(self) -> None:
        self.assertEqual([len(batch) for batch in batched_cars(self.cars, 2)], [2, 1])

    def test_rejects_zero_batch_size(self) -> None:
        with self.assertRaises(ValueError):
            list(batched_cars(self.cars, 0))

    def test_groupby_after_sorting(self) -> None:
        self.assertEqual(count_by_brand_sorted(self.cars), {"BMW": 1, "Toyota": 2})

    def test_generator_is_reproducible(self) -> None:
        self.assertEqual(list(generate_rows(5)), list(generate_rows(5)))


if __name__ == "__main__":
    unittest.main()
