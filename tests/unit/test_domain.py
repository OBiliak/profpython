"""Unit tests of the object-oriented domain (laboratory work 4)."""

import unittest
from dataclasses import FrozenInstanceError

from car_catalog.domain.dto import VehiclePayload, vehicle_from_payload, vehicle_to_payload
from car_catalog.domain.exceptions import (
    CatalogError,
    DuplicateEntityError,
    EmptyCatalogError,
    EntityNotFoundError,
    InvalidVehicleError,
)
from car_catalog.domain.models import Car, ElectricCar, Vehicle, VehicleCatalog
from car_catalog.domain.protocols import Describable
from car_catalog.domain.repositories import InMemoryRepository, UnitOfWork
from car_catalog.domain.services import CatalogService, MemoryLogger, QueryService, ServiceContainer
from car_catalog.domain.specifications import (
    BrandSpecification,
    MaxPriceSpecification,
    ModelSpecification,
    YearRangeSpecification,
)
from car_catalog.domain.statistics import average, largest, smallest
from car_catalog.domain.value_objects import Mileage, Money


def make_car(vehicle_id: int = 1, brand: str = "Toyota", year: int = 2018) -> Car:
    """Return a test car."""
    return Car(vehicle_id, brand, "Corolla", year, Money(500_000), Mileage(80_000))


class TestValueObjects(unittest.TestCase):
    """Tests of Money and Mileage."""

    def test_money_addition(self) -> None:
        self.assertEqual(Money(100) + Money(50), Money(150))

    def test_money_comparison_with_total_ordering(self) -> None:
        self.assertTrue(Money(200) > Money(100))
        self.assertTrue(Money(100) <= Money(100))

    def test_money_is_frozen(self) -> None:
        money = Money(100)
        with self.assertRaises(FrozenInstanceError):
            money.amount = 200  # type: ignore[misc]

    def test_money_negative_amount_raises(self) -> None:
        with self.assertRaises(InvalidVehicleError):
            Money(-1)

    def test_money_different_currency_raises(self) -> None:
        with self.assertRaises(InvalidVehicleError):
            Money(100) + Money(100, "USD")

    def test_mileage_addition_and_negative(self) -> None:
        self.assertEqual(Mileage(100) + Mileage(20), Mileage(120))
        with self.assertRaises(InvalidVehicleError):
            Mileage(-5)


class TestVehicles(unittest.TestCase):
    """Tests of Vehicle, Car and ElectricCar."""

    def test_vehicle_is_abstract(self) -> None:
        with self.assertRaises(TypeError):
            Vehicle(1, "Toyota", "Corolla", 2018, Money(1), Mileage(1))  # type: ignore[abstract]

    def test_price_setter_validates(self) -> None:
        car = make_car()
        car.price = Money(450_000)
        self.assertEqual(car.price, Money(450_000))
        with self.assertRaises(InvalidVehicleError):
            car.price = Money(0)

    def test_invalid_year_raises(self) -> None:
        with self.assertRaises(InvalidVehicleError):
            make_car(year=1900)

    def test_electric_car_inherits_car(self) -> None:
        tesla = ElectricCar(2, "Tesla", "Model 3", 2022, Money(1_450_000), Mileage(28_000), 75, 510)
        self.assertIsInstance(tesla, Car)
        self.assertEqual(tesla.kind(), "Електромобіль")
        self.assertIn("запас ходу 510 км", tesla.describe())

    def test_equality_by_id_and_repr(self) -> None:
        self.assertEqual(make_car(1), make_car(1, brand="Skoda"))
        self.assertNotEqual(make_car(1), make_car(2))
        self.assertEqual(repr(make_car(1)), "Car(id=1, brand='Toyota', model='Corolla', year=2018)")

    def test_runtime_checkable_protocol(self) -> None:
        self.assertIsInstance(make_car(), Describable)
        self.assertNotIsInstance(Money(1), Describable)


class TestVehicleCatalog(unittest.TestCase):
    """Tests of the custom collection."""

    def setUp(self) -> None:
        self.catalog = VehicleCatalog("Тест", [make_car(1), make_car(2, "BMW")])

    def test_len_getitem_iter(self) -> None:
        self.assertEqual(len(self.catalog), 2)
        self.assertEqual(self.catalog[1].brand, "BMW")
        self.assertEqual([vehicle.id for vehicle in self.catalog], [1, 2])

    def test_contains_by_object_and_id(self) -> None:
        self.assertIn(2, self.catalog)
        self.assertIn(make_car(1), self.catalog)
        self.assertNotIn(3, self.catalog)

    def test_add_duplicate_raises(self) -> None:
        with self.assertRaises(DuplicateEntityError):
            self.catalog.add(make_car(1))

    def test_default_factory_gives_new_list(self) -> None:
        first = VehicleCatalog("A")
        first.add(make_car())
        self.assertEqual(len(VehicleCatalog("B")), 0)


class TestRepositoryAndUnitOfWork(unittest.TestCase):
    """Tests of the generic repository and unit of work."""

    def setUp(self) -> None:
        self.repository: InMemoryRepository[Car] = InMemoryRepository()

    def test_add_get_remove(self) -> None:
        self.repository.add(make_car(1))
        self.assertEqual(self.repository.get(1).brand, "Toyota")
        self.repository.remove(1)
        self.assertIsNone(self.repository.find(1))

    def test_errors_are_catalog_errors(self) -> None:
        self.repository.add(make_car(1))
        with self.assertRaises(DuplicateEntityError):
            self.repository.add(make_car(1))
        with self.assertRaises(EntityNotFoundError):
            self.repository.get(5)
        self.assertTrue(issubclass(EntityNotFoundError, CatalogError))

    def test_unit_of_work_commit(self) -> None:
        with UnitOfWork(self.repository) as unit:
            unit.register_new(make_car(1))
            unit.register_new(make_car(2))
            self.assertEqual(unit.commit(), 2)
        self.assertEqual(len(self.repository), 2)

    def test_unit_of_work_saves_nothing_on_duplicate(self) -> None:
        self.repository.add(make_car(2))
        with self.assertRaises(DuplicateEntityError):
            with UnitOfWork(self.repository) as unit:
                unit.register_new(make_car(1))
                unit.register_new(make_car(2))
                unit.commit()
        self.assertIsNone(self.repository.find(1))


class TestSpecifications(unittest.TestCase):
    """Tests of search criteria."""

    def test_brand_and_model(self) -> None:
        car = make_car()
        self.assertTrue(BrandSpecification("toyota")(car))
        self.assertTrue(ModelSpecification("COROL").is_satisfied_by(car))
        self.assertFalse(BrandSpecification("BMW")(car))

    def test_year_range_and_combination(self) -> None:
        criteria = YearRangeSpecification(2015, 2019) & MaxPriceSpecification(Money(600_000))
        self.assertTrue(criteria(make_car(year=2018)))
        self.assertFalse(criteria(make_car(year=2020)))


class TestCatalogService(unittest.TestCase):
    """Tests of the application service with injected dependencies."""

    def setUp(self) -> None:
        self.logger = MemoryLogger()
        self.container = ServiceContainer(self.logger)
        self.service = self.container.catalog_service()
        self.service.add_vehicle(make_car(1, "Toyota", 2018))
        self.service.add_vehicle(Car(2, "BMW", "X5", 2020, Money(1_900_000), Mileage(50_000)))
        self.service.add_vehicle(
            ElectricCar(3, "Tesla", "Model 3", 2022, Money(1_400_000), Mileage(20_000), 75, 510)
        )

    def test_logger_is_injected(self) -> None:
        self.assertEqual(len(self.logger.messages), 3)
        self.assertEqual(self.logger.messages[0], "додано Toyota Corolla (ID 1)")

    def test_search_methods(self) -> None:
        self.assertEqual([v.id for v in self.service.find_by_brand("bmw")], [2])
        self.assertEqual([v.id for v in self.service.find_by_model("model")], [3])
        self.assertEqual([v.id for v in self.service.filter_by_year(2019)], [2, 3])

    def test_statistics(self) -> None:
        self.assertEqual(self.service.most_expensive().id, 2)
        self.assertEqual(self.service.lowest_mileage().id, 3)
        self.assertAlmostEqual(self.service.average_price().amount, 1_266_666.67, places=2)
        self.assertEqual(self.service.summary().count, 3)

    def test_empty_catalog_raises(self) -> None:
        service = ServiceContainer(MemoryLogger()).catalog_service()
        with self.assertRaises(EmptyCatalogError):
            service.most_expensive()

    def test_service_works_with_any_repository(self) -> None:
        repository: InMemoryRepository[Vehicle] = InMemoryRepository()
        service = CatalogService(repository, repository, MemoryLogger())
        service.add_vehicle(make_car(7))
        self.assertEqual(len(repository), 1)

    def test_generic_query_service(self) -> None:
        queries: QueryService[Vehicle] = self.container.query_service()
        self.assertEqual(queries.count(), 3)
        self.assertEqual(len(queries.find(lambda v: isinstance(v, ElectricCar))), 1)
        self.assertIsNone(queries.first(BrandSpecification("Audi")))


class TestPayloadAndStatistics(unittest.TestCase):
    """Tests of TypedDict conversion and constrained TypeVar helpers."""

    def test_payload_round_trip(self) -> None:
        payload: VehiclePayload = {
            "id": 9,
            "kind": "electric",
            "brand": "Nissan",
            "model": "Leaf",
            "year": 2019,
            "price": 560_000.0,
            "mileage": 41_000,
            "battery_kwh": 40.0,
            "range_km": 270,
        }
        vehicle = vehicle_from_payload(payload)
        self.assertIsInstance(vehicle, ElectricCar)
        self.assertEqual(vehicle_to_payload(vehicle), payload)

    def test_invalid_payload_raises(self) -> None:
        payload: VehiclePayload = {
            "id": 1,
            "kind": "electric",
            "brand": "Renault",
            "model": "Zoe",
            "year": 2020,
            "price": 430_000.0,
            "mileage": 52_000,
        }
        with self.assertRaises(InvalidVehicleError):
            vehicle_from_payload(payload)

    def test_constrained_typevar_helpers(self) -> None:
        self.assertEqual(smallest([2018, 2012, 2022]), 2012)
        self.assertEqual(largest([1.5, 2.5]), 2.5)
        self.assertEqual(average([1, 2, 3]), 2.0)
        with self.assertRaises(ValueError):
            largest([])


if __name__ == "__main__":
    unittest.main()
