"""Service layer over the database: functions of laboratory work 1, aggregates and transactions."""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from car_catalog.persistence.models import Car, Manufacturer
from car_catalog.persistence.repositories import CarRepository, ManufacturerRepository


@dataclass(frozen=True)
class ManufacturerStatistics:
    """One row of GROUP BY manufacturer: number of cars, average and total price."""

    name: str
    car_count: int
    average_price: float
    total_price: float


class CarCatalogService:
    """Business logic of the catalog; data access goes through repositories and SQL queries."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.cars = CarRepository(session)
        self.manufacturers = ManufacturerRepository(session)

    def find_by_brand(self, brand: str) -> list[Car]:
        """Search by brand (function of laboratory work 1)."""
        return self.cars.find_by_brand(brand)

    def filter_by_year(self, min_year: int, max_year: int) -> list[Car]:
        """Filter by year of manufacture (function of laboratory work 1)."""
        if min_year > max_year:
            raise ValueError("Початковий рік не може бути більшим за кінцевий")
        return self.cars.filter_by_year(min_year, max_year)

    def get_most_expensive(self) -> Car | None:
        """The most expensive car: ORDER BY price DESC LIMIT 1."""
        return self.session.scalar(select(Car).order_by(Car.price.desc(), Car.id).limit(1))

    def get_lowest_mileage(self) -> Car | None:
        """The car with the lowest mileage: ORDER BY mileage LIMIT 1."""
        return self.session.scalar(select(Car).order_by(Car.mileage, Car.id).limit(1))

    def get_average_price(self) -> float:
        """Average price via SQL AVG(); 0.0 for an empty table."""
        result = self.session.scalar(select(func.avg(Car.price)))
        return 0.0 if result is None else float(result)

    def count_cars(self) -> int:
        """Number of cars via SQL COUNT()."""
        return self.session.scalar(select(func.count(Car.id))) or 0

    def get_total_value(self) -> float:
        """Total price of all cars via SQL SUM()."""
        result = self.session.scalar(select(func.sum(Car.price)))
        return 0.0 if result is None else float(result)

    def statistics_by_manufacturer(self) -> list[ManufacturerStatistics]:
        """COUNT, AVG and SUM of prices per manufacturer (JOIN + GROUP BY), the largest total first."""
        statement = (
            select(
                Manufacturer.name,
                func.count(Car.id),
                func.avg(Car.price),
                func.sum(Car.price),
            )
            .join(Car, Car.manufacturer_id == Manufacturer.id)
            .group_by(Manufacturer.name)
            .order_by(func.sum(Car.price).desc())
        )
        return [
            ManufacturerStatistics(name, count, float(average), float(total))
            for name, count, average, total in self.session.execute(statement)
        ]

