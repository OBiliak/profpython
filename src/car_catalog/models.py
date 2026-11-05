"""Data models of the car catalog."""

from dataclasses import dataclass

from car_catalog.config import MAX_YEAR, MIN_YEAR


@dataclass(slots=True, frozen=True)
class Car:
    """A car in the catalog with brand, model, year, price and mileage."""

    brand: str
    model: str
    year: int
    price: float
    mileage: int

    def __post_init__(self) -> None:
        """Validate car fields after creation."""
        if not self.brand.strip():
            raise ValueError("Марка не може бути порожньою.")
        if not self.model.strip():
            raise ValueError("Модель не може бути порожньою.")
        if not MIN_YEAR <= self.year <= MAX_YEAR:
            raise ValueError(f"Рік має бути від {MIN_YEAR} до {MAX_YEAR}.")
        if self.price <= 0:
            raise ValueError("Ціна має бути більшою за нуль.")
        if self.mileage < 0:
            raise ValueError("Пробіг не може бути від'ємним.")
