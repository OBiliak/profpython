"""Repository Pattern: ManufacturerRepository and CarRepository hide SQLAlchemy queries."""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from car_catalog.persistence.exceptions import DatabaseConstraintError
from car_catalog.persistence.models import Car, Manufacturer

SORT_FIELDS = {
    "id": Car.id,
    "year": Car.year,
    "price": Car.price,
    "mileage": Car.mileage,
}


def commit_or_raise(session: Session) -> None:
    """Commit the session; on a constraint error roll back and raise DatabaseConstraintError."""
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise DatabaseConstraintError(f"База даних відхилила запис: {error.orig}") from error


class ManufacturerRepository:
    """CRUD of manufacturers."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, name: str, country: str) -> Manufacturer:
        """Create a manufacturer."""
        manufacturer = Manufacturer(name=name, country=country)
        self.session.add(manufacturer)
        commit_or_raise(self.session)
        return manufacturer

    def get_by_id(self, manufacturer_id: int) -> Manufacturer | None:
        """Return a manufacturer by ID or None."""
        return self.session.get(Manufacturer, manufacturer_id)

    def get_by_name(self, name: str) -> Manufacturer | None:
        """Return a manufacturer by name (case-insensitive) or None."""
        statement = select(Manufacturer).where(
            func.lower(Manufacturer.name) == name.strip().lower()
        )
        return self.session.scalar(statement)

    def get_all(self) -> list[Manufacturer]:
        """Return all manufacturers sorted by name."""
        return list(self.session.scalars(select(Manufacturer).order_by(Manufacturer.name)))

    def update_country(self, manufacturer_id: int, country: str) -> Manufacturer | None:
        """Change the country of a manufacturer; None if it does not exist."""
        manufacturer = self.get_by_id(manufacturer_id)
        if manufacturer is None:
            return None
        manufacturer.country = country
        commit_or_raise(self.session)
        return manufacturer

    def delete(self, manufacturer_id: int) -> bool:
        """Delete a manufacturer together with its cars (cascade)."""
        manufacturer = self.get_by_id(manufacturer_id)
        if manufacturer is None:
            return False
        self.session.delete(manufacturer)
        self.session.commit()
        return True


class CarRepository:
    """CRUD, search, filters, sorting and pagination of cars."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, car: Car) -> Car:
        """Create a car."""
        self.session.add(car)
        commit_or_raise(self.session)
        return car

    def get_by_id(self, car_id: int) -> Car | None:
        """Return a car by ID or None."""
        return self.session.get(Car, car_id)

    def get_all(
        self,
        order_by: str = "id",
        descending: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Car]:
        """Return cars sorted by a field; limit and offset give one page."""
        column = SORT_FIELDS[order_by]
        statement = select(Car).order_by(column.desc() if descending else column, Car.id)
        statement = statement.offset(offset).limit(limit)
        return list(self.session.scalars(statement))

    def get_page(
        self, page: int, page_size: int, order_by: str = "id", descending: bool = False
    ) -> list[Car]:
        """Return page number `page` (from 1) of size `page_size`."""
        if page < 1 or page_size < 1:
            raise ValueError("page і page_size мають бути додатними")
        return self.get_all(order_by, descending, limit=page_size, offset=(page - 1) * page_size)

    def find_by_brand(self, brand: str) -> list[Car]:
        """Return cars of a brand (JOIN with manufacturers, case-insensitive)."""
        statement = (
            select(Car)
            .join(Manufacturer, Car.manufacturer_id == Manufacturer.id)
            .where(func.lower(Manufacturer.name) == brand.strip().lower())
            .order_by(Car.id)
        )
        return list(self.session.scalars(statement))

    def filter_by_year(self, min_year: int, max_year: int) -> list[Car]:
        """Return cars with min_year <= year <= max_year."""
        statement = (
            select(Car).where(Car.year.between(min_year, max_year)).order_by(Car.year, Car.id)
        )
        return list(self.session.scalars(statement))

    def find(
        self,
        brand: str | None = None,
        min_year: int | None = None,
        max_price: float | None = None,
        max_mileage: int | None = None,
    ) -> list[Car]:
        """Complex filter: only the given conditions are added to WHERE (joined with AND)."""
        statement = select(Car).join(Car.manufacturer)
        if brand is not None:
            statement = statement.where(func.lower(Manufacturer.name) == brand.strip().lower())
        if min_year is not None:
            statement = statement.where(Car.year >= min_year)
        if max_price is not None:
            statement = statement.where(Car.price <= max_price)
        if max_mileage is not None:
            statement = statement.where(Car.mileage <= max_mileage)
        return list(self.session.scalars(statement.order_by(Car.price)))

    def search(
        self,
        brand: str | None = None,
        model: str | None = None,
        min_year: int | None = None,
        max_year: int | None = None,
        order_by: str = "id",
        descending: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Car]:
        """Search by brand and part of the model, filter by years, sort and return one page."""
        statement = select(Car).join(Car.manufacturer)
        if brand is not None:
            statement = statement.where(func.lower(Manufacturer.name) == brand.strip().lower())
        if model is not None:
            statement = statement.where(Car.model.icontains(model.strip()))
        if min_year is not None:
            statement = statement.where(Car.year >= min_year)
        if max_year is not None:
            statement = statement.where(Car.year <= max_year)
        column = SORT_FIELDS[order_by]
        statement = statement.order_by(column.desc() if descending else column, Car.id)
        return list(self.session.scalars(statement.offset(offset).limit(limit)))

    def list_with_manufacturer(self) -> list[tuple[int, str, str, str, int]]:
        """JOIN cars and manufacturers: (id, brand, model, country, year) for every car."""
        statement = (
            select(Car.id, Manufacturer.name, Car.model, Manufacturer.country, Car.year)
            .join(Manufacturer, Car.manufacturer_id == Manufacturer.id)
            .order_by(Car.id)
        )
        return [
            (car_id, brand, model, country, year)
            for car_id, brand, model, country, year in self.session.execute(statement)
        ]

    def update_price(self, car_id: int, price: float) -> Car | None:
        """Change the price of a car; None if it does not exist."""
        car = self.get_by_id(car_id)
        if car is None:
            return None
        car.price = price
        commit_or_raise(self.session)
        return car

    def update_mileage(self, car_id: int, mileage: int) -> Car | None:
        """Change the mileage of a car; None if it does not exist."""
        car = self.get_by_id(car_id)
        if car is None:
            return None
        car.mileage = mileage
        commit_or_raise(self.session)
        return car

    def delete(self, car_id: int) -> bool:
        """Delete a car; False if it does not exist."""
        car = self.get_by_id(car_id)
        if car is None:
            return False
        self.session.delete(car)
        self.session.commit()
        return True
