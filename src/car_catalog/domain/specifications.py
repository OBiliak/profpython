"""Search criteria abstraction: specifications as interchangeable strategies."""

from abc import ABC, abstractmethod

from car_catalog.domain.models import Vehicle
from car_catalog.domain.value_objects import Money


class VehicleSpecification(ABC):
    """A search criterion that a vehicle can satisfy."""

    @abstractmethod
    def is_satisfied_by(self, vehicle: Vehicle) -> bool:
        """Return True if the vehicle matches the criterion."""

    def __call__(self, vehicle: Vehicle) -> bool:
        """Allow using a specification as a function-predicate."""
        return self.is_satisfied_by(vehicle)

    def __and__(self, other: "VehicleSpecification") -> "AndSpecification":
        """Combine two criteria: spec1 & spec2."""
        return AndSpecification(self, other)


class BrandSpecification(VehicleSpecification):
    """Vehicles of the given brand (case-insensitive)."""

    def __init__(self, brand: str) -> None:
        self.brand = brand.strip().lower()

    def is_satisfied_by(self, vehicle: Vehicle) -> bool:
        """Return True if the brand matches."""
        return vehicle.brand.lower() == self.brand


class ModelSpecification(VehicleSpecification):
    """Vehicles whose model contains the given text (case-insensitive)."""

    def __init__(self, model: str) -> None:
        self.model = model.strip().lower()

    def is_satisfied_by(self, vehicle: Vehicle) -> bool:
        """Return True if the model contains the text; an empty text matches nothing."""
        return bool(self.model) and self.model in vehicle.model.lower()


class YearRangeSpecification(VehicleSpecification):
    """Vehicles made from min_year to max_year inclusive."""

    def __init__(self, min_year: int, max_year: int | None = None) -> None:
        self.min_year = min_year
        self.max_year = max_year

    def is_satisfied_by(self, vehicle: Vehicle) -> bool:
        """Return True if the year is in the range."""
        if vehicle.year < self.min_year:
            return False
        return self.max_year is None or vehicle.year <= self.max_year


class MaxPriceSpecification(VehicleSpecification):
    """Vehicles not more expensive than the given price."""

    def __init__(self, max_price: Money) -> None:
        self.max_price = max_price

    def is_satisfied_by(self, vehicle: Vehicle) -> bool:
        """Return True if the price is not greater than max_price."""
        return vehicle.price <= self.max_price


class AndSpecification(VehicleSpecification):
    """Vehicles that satisfy all given criteria."""

    def __init__(self, *specifications: VehicleSpecification) -> None:
        self.specifications = specifications

    def is_satisfied_by(self, vehicle: Vehicle) -> bool:
        """Return True if every criterion is satisfied."""
        return all(spec.is_satisfied_by(vehicle) for spec in self.specifications)
