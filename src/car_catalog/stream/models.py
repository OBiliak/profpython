"""Record model of the streaming car pipeline."""

from typing import NamedTuple


class CarRecord(NamedTuple):
    """One validated car record from the CSV stream."""

    id: int
    brand: str
    model: str
    year: int
    price: float
    mileage: int
