"""Small Protocols (interface segregation) used by repositories and services."""

from typing import Protocol, runtime_checkable

from car_catalog.domain.models import Vehicle


class HasId(Protocol):
    """Any object with an integer ID."""

    @property
    def id(self) -> int:
        """Return the ID."""
        ...


@runtime_checkable
class Describable(Protocol):
    """Any object that can describe itself as text."""

    def describe(self) -> str:
        """Return a description."""
        ...


class VehicleReader(Protocol):
    """Read access to stored vehicles."""

    def get(self, item_id: int) -> Vehicle:
        """Return a vehicle by ID."""
        ...

    def all(self) -> list[Vehicle]:
        """Return all vehicles."""
        ...


class VehicleWriter(Protocol):
    """Write access to stored vehicles."""

    def add(self, item: Vehicle) -> None:
        """Store a vehicle."""
        ...

    def remove(self, item_id: int) -> None:
        """Delete a vehicle by ID."""
        ...


class EventLogger(Protocol):
    """Anything that can record a message about an operation."""

    def log(self, message: str) -> None:
        """Record a message."""
        ...
