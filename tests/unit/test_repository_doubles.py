"""Unit tests of CatalogService with a Mock repository and with a fake repository."""

from collections.abc import Callable
from unittest.mock import Mock

import pytest
from conftest import FakeVehicleRepository

from car_catalog.domain.exceptions import EntityNotFoundError
from car_catalog.domain.models import Car
from car_catalog.domain.protocols import EventLogger, VehicleReader, VehicleWriter
from car_catalog.domain.repositories import InMemoryRepository
from car_catalog.domain.services import CatalogService


def test_service_reads_vehicles_from_mock_repository(make_car: Callable[..., Car]) -> None:
    reader = Mock(spec=VehicleReader)
    reader.all.return_value = [
        make_car(1, price=520_000),
        make_car(5, "BMW", "X5", price=1_890_000),
    ]
    service = CatalogService(reader, Mock(spec=VehicleWriter), Mock(spec=EventLogger))

    assert service.most_expensive().id == 5
    reader.all.assert_called_once_with()


def test_add_vehicle_calls_writer_and_logger(make_car: Callable[..., Car]) -> None:
    writer = Mock(spec=VehicleWriter)
    logger = Mock(spec=EventLogger)
    service = CatalogService(Mock(spec=VehicleReader), writer, logger)
    car = make_car(2, "Toyota", "RAV4")

    service.add_vehicle(car)

    writer.add.assert_called_once_with(car)
    logger.log.assert_called_once_with("додано Toyota RAV4 (ID 2)")


def test_failed_remove_is_not_logged() -> None:
    writer = Mock(spec=VehicleWriter)
    writer.remove.side_effect = EntityNotFoundError(99)
    logger = Mock(spec=EventLogger)
    service = CatalogService(Mock(spec=VehicleReader), writer, logger)

    with pytest.raises(EntityNotFoundError, match="ID 99"):
        service.remove_vehicle(99)

    logger.log.assert_not_called()


def test_fake_repository_keeps_state(
    catalog_service: CatalogService, repository: FakeVehicleRepository
) -> None:
    catalog_service.remove_vehicle(1)

    assert sorted(repository.items) == [2, 4, 5, 6]
    assert catalog_service.get_vehicle(2).model == "RAV4"


def test_in_memory_repository_rejects_removing_unknown_id() -> None:
    repository = InMemoryRepository[Car]()

    with pytest.raises(EntityNotFoundError, match="ID 7"):
        repository.remove(7)


def test_vehicle_is_not_equal_to_other_object(make_car: Callable[..., Car]) -> None:
    car = make_car()

    assert car != "Toyota Corolla"
    assert car == make_car()
