"""SQLAlchemy ORM models: tables manufacturers and cars (one-to-many)."""

from __future__ import annotations

from sqlalchemy import CheckConstraint, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

MIN_YEAR = 1950
MAX_YEAR = 2026


class Base(DeclarativeBase):
    """Base class of all ORM models."""


class Manufacturer(Base):
    """Car manufacturer (brand); one manufacturer has many cars."""

    __tablename__ = "manufacturers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)

    cars: Mapped[list[Car]] = relationship(
        back_populates="manufacturer",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"Manufacturer(id={self.id}, name={self.name!r}, country={self.country!r})"


class Car(Base):
    """Car of the catalog: model, year, price, mileage, VIN and the manufacturer (brand)."""

    __tablename__ = "cars"
    __table_args__ = (
        CheckConstraint(f"year BETWEEN {MIN_YEAR} AND {MAX_YEAR}", name="ck_cars_year"),
        CheckConstraint("price > 0", name="ck_cars_price"),
        CheckConstraint("mileage >= 0", name="ck_cars_mileage"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    mileage: Mapped[int] = mapped_column(Integer, nullable=False)
    vin: Mapped[str | None] = mapped_column(String(17), unique=True, index=True, nullable=True)
    manufacturer_id: Mapped[int] = mapped_column(
        ForeignKey("manufacturers.id", ondelete="CASCADE"),
        nullable=False,
    )

    manufacturer: Mapped[Manufacturer] = relationship(back_populates="cars")

    @property
    def brand(self) -> str:
        """Brand of the car = name of its manufacturer."""
        return self.manufacturer.name

    def describe(self) -> str:
        """Return a short text description of the car."""
        return f"{self.brand} {self.model}, {self.year} р., {self.price:.2f} грн, {self.mileage} км"

    def __repr__(self) -> str:
        return f"Car(id={self.id}, model={self.model!r}, year={self.year})"
