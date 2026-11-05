"""Design experiments: service without DI vs DI, inheritance vs composition."""

from abc import ABC, abstractmethod
from typing import Protocol

from car_catalog.domain.models import Car, Vehicle
from car_catalog.domain.repositories import InMemoryRepository
from car_catalog.domain.services import CatalogService, ConsoleLogger, MemoryLogger
from car_catalog.domain.value_objects import Mileage, Money

CSV_LINES = [
    "1,Toyota,Corolla,2018,520000,85000",
    "2,Volkswagen,Golf,2012,380000,142000",
    "3,BMW,X5,2020,1890000,54000",
]


# --- Variant A: the service creates concrete dependencies itself ---


class CatalogServiceWithoutDI:
    """Service that creates its repository and logger inside the constructor."""

    def __init__(self) -> None:
        self.repository: InMemoryRepository[Vehicle] = InMemoryRepository()
        self.logger = ConsoleLogger()

    def add_vehicle(self, vehicle: Vehicle) -> None:
        """Add a vehicle and print a log message."""
        self.repository.add(vehicle)
        self.logger.log(f"додано {vehicle.brand} {vehicle.model} (ID {vehicle.id})")


def compare_dependency_injection() -> None:
    """Show why variant B (DI) is easier to test and to change."""
    print("--- Експеримент 1: A (service створює залежності) vs B (DI) ---")
    corolla = Car(1, "Toyota", "Corolla", 2018, Money(520_000), Mileage(85_000))

    print("A: CatalogServiceWithoutDI() — logger завжди ConsoleLogger, пише в консоль:")
    service_a = CatalogServiceWithoutDI()
    service_a.add_vehicle(corolla)
    print("   перевірити повідомлення в тесті можна лише перехопленням stdout")

    print("B: CatalogService(repository, repository, MemoryLogger()) — нічого не друкує:")
    repository: InMemoryRepository[Vehicle] = InMemoryRepository()
    logger = MemoryLogger()
    service_b = CatalogService(repository, repository, logger)
    service_b.add_vehicle(corolla)
    print(f"   logger.messages = {logger.messages}")
    print(f"   у репозиторії {len(repository)} запис, ConsoleLogger замінено без зміни класу")


# --- Inheritance: BaseProcessor -> CsvProcessor ---


class BaseProcessor(ABC):
    """Template of processing: parse -> validate -> format."""

    def process(self, lines: list[str]) -> list[str]:
        """Return formatted valid vehicles from the lines."""
        result = []
        for line in lines:
            vehicle = self.parse(line)
            if self.is_valid(vehicle):
                result.append(self.format(vehicle))
        return result

    @abstractmethod
    def parse(self, line: str) -> Vehicle:
        """Create a vehicle from one line."""

    def is_valid(self, vehicle: Vehicle) -> bool:
        """Accept vehicles made from 2015."""
        return vehicle.year >= 2015

    def format(self, vehicle: Vehicle) -> str:
        """Return a short text about the vehicle."""
        return f"{vehicle.brand} {vehicle.model} ({vehicle.year})"


class CsvProcessor(BaseProcessor):
    """Processor of CSV lines (inherits validation and formatting)."""

    def parse(self, line: str) -> Vehicle:
        """Create a car from a CSV line."""
        return parse_csv_line(line)


class CsvPriceProcessor(CsvProcessor):
    """One more subclass is needed only to change the output format."""

    def format(self, vehicle: Vehicle) -> str:
        """Return the vehicle with its price."""
        return f"{vehicle.brand} {vehicle.model}: {vehicle.price}"


# --- Composition: Processor has Parser, Validator, Formatter ---


class Parser(Protocol):
    """Creates a vehicle from a line."""

    def parse(self, line: str) -> Vehicle:
        """Create a vehicle."""
        ...


class Validator(Protocol):
    """Decides whether a vehicle is accepted."""

    def is_valid(self, vehicle: Vehicle) -> bool:
        """Return True for an accepted vehicle."""
        ...


class Formatter(Protocol):
    """Turns a vehicle into text."""

    def format(self, vehicle: Vehicle) -> str:
        """Return text."""
        ...


class CsvParser:
    """Parser of CSV lines."""

    def parse(self, line: str) -> Vehicle:
        """Create a car from a CSV line."""
        return parse_csv_line(line)


class YearValidator:
    """Accepts vehicles made from min_year."""

    def __init__(self, min_year: int) -> None:
        self.min_year = min_year

    def is_valid(self, vehicle: Vehicle) -> bool:
        """Return True if the vehicle is not older than min_year."""
        return vehicle.year >= self.min_year


class ShortFormatter:
    """Brand, model and year."""

    def format(self, vehicle: Vehicle) -> str:
        """Return a short text about the vehicle."""
        return f"{vehicle.brand} {vehicle.model} ({vehicle.year})"


class PriceFormatter:
    """Brand, model and price."""

    def format(self, vehicle: Vehicle) -> str:
        """Return the vehicle with its price."""
        return f"{vehicle.brand} {vehicle.model}: {vehicle.price}"


class Processor:
    """Processor built from three replaceable parts."""

    def __init__(self, parser: Parser, validator: Validator, formatter: Formatter) -> None:
        self.parser = parser
        self.validator = validator
        self.formatter = formatter

    def process(self, lines: list[str]) -> list[str]:
        """Return formatted valid vehicles from the lines."""
        result = []
        for line in lines:
            vehicle = self.parser.parse(line)
            if self.validator.is_valid(vehicle):
                result.append(self.formatter.format(vehicle))
        return result


def parse_csv_line(line: str) -> Vehicle:
    """Create a car from the line id,brand,model,year,price,mileage."""
    vehicle_id, brand, model, year, price, mileage = line.split(",")
    return Car(int(vehicle_id), brand, model, int(year), Money(float(price)), Mileage(int(mileage)))


def compare_inheritance_and_composition() -> None:
    """Run the same behavior built by inheritance and by composition."""
    print("\n--- Експеримент 2: inheritance vs composition ---")
    print(f"Inheritance, CsvProcessor:           {CsvProcessor().process(CSV_LINES)}")
    print(f"Inheritance, CsvPriceProcessor:      {CsvPriceProcessor().process(CSV_LINES)}")
    short = Processor(CsvParser(), YearValidator(2015), ShortFormatter())
    print(f"Composition, ShortFormatter:         {short.process(CSV_LINES)}")
    priced = Processor(CsvParser(), YearValidator(2015), PriceFormatter())
    print(f"Composition, PriceFormatter:         {priced.process(CSV_LINES)}")
    newer = Processor(CsvParser(), YearValidator(2019), PriceFormatter())
    print(f"Composition, YearValidator(2019):    {newer.process(CSV_LINES)}")
    print("Inheritance: для кожної нової комбінації — новий subclass (CsvPriceProcessor).")
    print("Composition: нова комбінація — інші об'єкти в конструкторі, без нових класів.")


def main() -> None:
    """Run both design experiments of laboratory work 4."""
    compare_dependency_injection()
    compare_inheritance_and_composition()


if __name__ == "__main__":
    main()
