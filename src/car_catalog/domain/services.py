"""Application service layer, loggers and a manual dependency injection container."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic

from car_catalog.domain.exceptions import EmptyCatalogError
from car_catalog.domain.models import Vehicle, VehicleCatalog
from car_catalog.domain.protocols import EventLogger, VehicleReader, VehicleWriter
from car_catalog.domain.repositories import InMemoryRepository, Repository, T, UnitOfWork
from car_catalog.domain.specifications import (
    BrandSpecification,
    ModelSpecification,
    VehicleSpecification,
    YearRangeSpecification,
)
from car_catalog.domain.value_objects import Money


class ConsoleLogger:
    """Logger that prints messages to the console."""

    def log(self, message: str) -> None:
        """Print a message."""
        print(f"[log] {message}")


class MemoryLogger:
    """Logger that keeps messages in a list (useful for tests)."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    def log(self, message: str) -> None:
        """Save a message."""
        self.messages.append(message)


@dataclass(frozen=True)
class CatalogSummary:
    """Main statistics of the catalog."""

    count: int
    average_price: Money
    most_expensive: Vehicle
    lowest_mileage: Vehicle


class CatalogService:
    """Use cases of the car catalog; dependencies are passed to the constructor."""

    def __init__(self, reader: VehicleReader, writer: VehicleWriter, logger: EventLogger) -> None:
        self._reader = reader
        self._writer = writer
        self._logger = logger

    def add_vehicle(self, vehicle: Vehicle) -> None:
        """Add a vehicle to the storage."""
        self._writer.add(vehicle)
        self._logger.log(f"додано {vehicle.brand} {vehicle.model} (ID {vehicle.id})")

    def remove_vehicle(self, vehicle_id: int) -> None:
        """Delete a vehicle by ID."""
        self._writer.remove(vehicle_id)
        self._logger.log(f"видалено ID {vehicle_id}")

    def get_vehicle(self, vehicle_id: int) -> Vehicle:
        """Return a vehicle by ID."""
        return self._reader.get(vehicle_id)

    def search(self, specification: VehicleSpecification) -> list[Vehicle]:
        """Return vehicles that satisfy the specification."""
        return [vehicle for vehicle in self._reader.all() if specification(vehicle)]

    def find_by_brand(self, brand: str) -> list[Vehicle]:
        """Return vehicles of the brand."""
        return self.search(BrandSpecification(brand))

    def find_by_model(self, model: str) -> list[Vehicle]:
        """Return vehicles whose model contains the text."""
        return self.search(ModelSpecification(model))

    def filter_by_year(self, min_year: int, max_year: int | None = None) -> list[Vehicle]:
        """Return vehicles made in the range of years."""
        return self.search(YearRangeSpecification(min_year, max_year))

    def most_expensive(self) -> Vehicle:
        """Return the most expensive vehicle."""
        return max(self._all_or_error(), key=lambda vehicle: vehicle.price)

    def lowest_mileage(self) -> Vehicle:
        """Return the vehicle with the lowest mileage."""
        return min(self._all_or_error(), key=lambda vehicle: vehicle.mileage)

    def average_price(self) -> Money:
        """Return the average price of all vehicles."""
        vehicles = self._all_or_error()
        total = Money(0)
        for vehicle in vehicles:
            total = total + vehicle.price
        return total / len(vehicles)

    def summary(self) -> CatalogSummary:
        """Return the main statistics in one object."""
        return CatalogSummary(
            count=len(self._reader.all()),
            average_price=self.average_price(),
            most_expensive=self.most_expensive(),
            lowest_mileage=self.lowest_mileage(),
        )

    def build_catalog(self, name: str) -> VehicleCatalog:
        """Return all stored vehicles as a VehicleCatalog collection."""
        return VehicleCatalog(name, self._reader.all())

    def _all_or_error(self) -> list[Vehicle]:
        """Return all vehicles or raise EmptyCatalogError."""
        vehicles = self._reader.all()
        if not vehicles:
            raise EmptyCatalogError()
        return vehicles


class QueryService(Generic[T]):
    """Generic read-only service that works with a repository of any type T."""

    def __init__(self, repository: Repository[T]) -> None:
        self._repository = repository

    def count(self) -> int:
        """Return the number of items."""
        return len(self._repository.all())

    def find(self, predicate: Callable[[T], bool]) -> list[T]:
        """Return items for which the predicate is True."""
        return [item for item in self._repository.all() if predicate(item)]

    def first(self, predicate: Callable[[T], bool]) -> T | None:
        """Return the first item for which the predicate is True or None."""
        for item in self._repository.all():
            if predicate(item):
                return item
        return None


class ServiceContainer:
    """Manual DI container: creates dependencies once and wires the services."""

    def __init__(self, logger: EventLogger | None = None) -> None:
        self.repository: InMemoryRepository[Vehicle] = InMemoryRepository()
        self.logger: EventLogger = logger if logger is not None else ConsoleLogger()

    def catalog_service(self) -> CatalogService:
        """Return the catalog service with the shared repository and logger."""
        return CatalogService(self.repository, self.repository, self.logger)

    def query_service(self) -> QueryService[Vehicle]:
        """Return the generic query service for vehicles."""
        return QueryService(self.repository)

    def unit_of_work(self) -> UnitOfWork[Vehicle]:
        """Return a new unit of work for the shared repository."""
        return UnitOfWork(self.repository)
