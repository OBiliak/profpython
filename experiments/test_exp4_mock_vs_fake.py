"""Experiment 4: the same behavior tested with a Mock and with a fake repository."""

from unittest.mock import Mock

from car_catalog.domain.models import Car
from car_catalog.domain.protocols import VehicleReader, VehicleWriter
from car_catalog.domain.repositories import InMemoryRepository
from car_catalog.domain.services import CatalogService, MemoryLogger
from car_catalog.domain.value_objects import Mileage, Money

RAV4 = Car(2, "Toyota", "RAV4", 2021, Money(1_150_000), Mileage(32_000))


def test_remove_with_mock() -> None:
    writer = Mock(spec=VehicleWriter)
    service = CatalogService(Mock(spec=VehicleReader), writer, MemoryLogger())

    service.remove_vehicle(2)

    writer.remove.assert_called_once_with(2)


def test_remove_with_fake() -> None:
    repository = InMemoryRepository[Car]()
    service = CatalogService(repository, repository, MemoryLogger())
    service.add_vehicle(RAV4)

    service.remove_vehicle(2)

    assert service.find_by_brand("Toyota") == []
