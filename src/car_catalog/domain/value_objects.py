"""Immutable value objects: Money and Mileage."""

from dataclasses import dataclass
from functools import total_ordering

from car_catalog.domain.exceptions import InvalidVehicleError


@total_ordering
@dataclass(frozen=True, slots=True)
class Money:
    """An amount of money in one currency."""

    amount: float
    currency: str = "грн"

    def __post_init__(self) -> None:
        """Check that the amount is not negative."""
        if self.amount < 0:
            raise InvalidVehicleError("Сума грошей не може бути від'ємною.")

    def __add__(self, other: "Money") -> "Money":
        """Return the sum of two amounts in the same currency."""
        self._check_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __truediv__(self, number: int) -> "Money":
        """Return the amount divided by a number, for example for an average."""
        return Money(self.amount / number, self.currency)

    def __lt__(self, other: "Money") -> bool:
        """Compare two amounts in the same currency."""
        self._check_currency(other)
        return self.amount < other.amount

    def __str__(self) -> str:
        """Return the amount with two decimals and the currency."""
        return f"{self.amount:.2f} {self.currency}"

    def _check_currency(self, other: "Money") -> None:
        """Raise an error if the currencies are different."""
        if self.currency != other.currency:
            raise InvalidVehicleError("Валюти не збігаються.")


@total_ordering
@dataclass(frozen=True, slots=True)
class Mileage:
    """Mileage of a vehicle in kilometers."""

    km: int

    def __post_init__(self) -> None:
        """Check that the mileage is not negative."""
        if self.km < 0:
            raise InvalidVehicleError("Пробіг не може бути від'ємним.")

    def __add__(self, other: "Mileage") -> "Mileage":
        """Return the sum of two mileages."""
        return Mileage(self.km + other.km)

    def __lt__(self, other: "Mileage") -> bool:
        """Compare two mileages."""
        return self.km < other.km

    def __str__(self) -> str:
        """Return the mileage with units."""
        return f"{self.km} км"
