"""Domain entities: Vehicle (ABC), Car, ElectricCar and the VehicleCatalog collection."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field

from car_catalog.config import MAX_YEAR, MIN_YEAR
from car_catalog.domain.exceptions import DuplicateEntityError, InvalidVehicleError
from car_catalog.domain.value_objects import Mileage, Money


class Vehicle(ABC):
    """Abstract vehicle with common data and behavior of all vehicles."""

    wheels = 4

    def __init__(
        self,
        vehicle_id: int,
        brand: str,
        model: str,
        year: int,
        price: Money,
        mileage: Mileage,
    ) -> None:
        if not brand.strip() or not model.strip():
            raise InvalidVehicleError("Марка і модель не можуть бути порожніми.")
        if not MIN_YEAR <= year <= MAX_YEAR:
            raise InvalidVehicleError(f"Рік має бути від {MIN_YEAR} до {MAX_YEAR}.")
        self._id = vehicle_id
        self.brand = brand.strip()
        self.model = model.strip()
        self.year = year
        self.mileage = mileage
        self.price = price

    @property
    def id(self) -> int:
        """Return the vehicle ID (read-only)."""
        return self._id

    @property
    def price(self) -> Money:
        """Return the vehicle price."""
        return self._price

    @price.setter
    def price(self, value: Money) -> None:
        """Set a new price if it is greater than zero."""
        if value.amount <= 0:
            raise InvalidVehicleError("Ціна має бути більшою за нуль.")
        self._price = value

    @property
    def age(self) -> int:
        """Return the vehicle age in years."""
        return MAX_YEAR - self.year

    @abstractmethod
    def kind(self) -> str:
        """Return the type of the vehicle for the user."""

    def describe(self) -> str:
        """Return a short description of the vehicle."""
        return (
            f"{self.kind()} {self.brand} {self.model}, {self.year} р., "
            f"{self.price}, {self.mileage}"
        )

    def __repr__(self) -> str:
        """Return a technical representation for debugging."""
        return (
            f"{type(self).__name__}(id={self.id}, brand={self.brand!r}, "
            f"model={self.model!r}, year={self.year})"
        )

    def __str__(self) -> str:
        """Return a readable description for the user."""
        return self.describe()

    def __eq__(self, other: object) -> bool:
        """Vehicles are equal if they have the same type and ID."""
        if not isinstance(other, Vehicle):
            return NotImplemented
        return type(self) is type(other) and self.id == other.id

    def __hash__(self) -> int:
        """Return a hash based on the ID."""
        return hash(self.id)


class Car(Vehicle):
    """A car with an internal combustion engine and a body type."""

    def __init__(
        self,
        vehicle_id: int,
        brand: str,
        model: str,
        year: int,
        price: Money,
        mileage: Mileage,
        body_type: str = "седан",
    ) -> None:
        super().__init__(vehicle_id, brand, model, year, price, mileage)
        self.body_type = body_type

    def kind(self) -> str:
        """Return the type of the vehicle."""
        return "Автомобіль"


class ElectricCar(Car):
    """An electric car with battery capacity and range."""

    def __init__(
        self,
        vehicle_id: int,
        brand: str,
        model: str,
        year: int,
        price: Money,
        mileage: Mileage,
        battery_kwh: float,
        range_km: int,
        body_type: str = "седан",
    ) -> None:
        super().__init__(vehicle_id, brand, model, year, price, mileage, body_type)
        if battery_kwh <= 0 or range_km <= 0:
            raise InvalidVehicleError("Ємність батареї і запас ходу мають бути більшими за нуль.")
        self.battery_kwh = battery_kwh
        self.range_km = range_km

    def kind(self) -> str:
        """Return the type of the vehicle."""
        return "Електромобіль"

    def describe(self) -> str:
        """Return the description with battery data."""
        return f"{super().describe()}, батарея {self.battery_kwh} кВт·год, запас ходу {self.range_km} км"


@dataclass
class VehicleCatalog:
    """A named collection of vehicles (composition: the catalog has vehicles)."""

    name: str
    vehicles: list[Vehicle] = field(default_factory=list)

    def add(self, vehicle: Vehicle) -> None:
        """Add a vehicle if a vehicle with the same ID is not in the catalog."""
        if vehicle.id in self:
            raise DuplicateEntityError(vehicle.id)
        self.vehicles.append(vehicle)

    def __len__(self) -> int:
        """Return the number of vehicles."""
        return len(self.vehicles)

    def __iter__(self) -> Iterator[Vehicle]:
        """Iterate over vehicles."""
        return iter(self.vehicles)

    def __getitem__(self, index: int) -> Vehicle:
        """Return a vehicle by position."""
        return self.vehicles[index]

    def __contains__(self, item: object) -> bool:
        """Check whether a vehicle or a vehicle ID is in the catalog."""
        if isinstance(item, int):
            return any(vehicle.id == item for vehicle in self.vehicles)
        return item in self.vehicles
