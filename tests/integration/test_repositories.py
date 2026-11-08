"""Integration tests: repositories + SQLAlchemy ORM + a test SQLite database."""

from collections.abc import Callable

import pytest
from sqlalchemy.orm import Session

from car_catalog.persistence.exceptions import DatabaseConstraintError
from car_catalog.persistence.models import Car
from car_catalog.persistence.repositories import CarRepository, ManufacturerRepository

pytestmark = pytest.mark.integration

MakeCar = Callable[..., Car]


# --- Create ---


def test_add_manufacturer(session: Session) -> None:
    saved = ManufacturerRepository(session).add("Toyota", "Японія")

    assert saved.id is not None
    assert ManufacturerRepository(session).get_by_name("toyota") == saved


def test_add_car(session: Session, make_db_car: MakeCar) -> None:
    toyota = ManufacturerRepository(session).add("Toyota", "Японія")

    saved = CarRepository(session).add(make_db_car(toyota.id, vin="JTDBR32E720000001"))

    assert saved.id is not None
    assert saved.brand == "Toyota"
    assert saved.describe() == "Toyota Corolla, 2018 р., 520000.00 грн, 85000 км"


# --- Read ---


def test_get_car_by_id(seeded_session: Session) -> None:
    car = CarRepository(seeded_session).get_by_id(5)

    assert car is not None
    assert (car.brand, car.model, car.year) == ("BMW", "X5", 2020)


def test_get_missing_car_returns_none(seeded_session: Session) -> None:
    assert CarRepository(seeded_session).get_by_id(999) is None


def test_get_all_returns_every_car_sorted_by_id(seeded_session: Session) -> None:
    cars = CarRepository(seeded_session).get_all()

    assert [car.id for car in cars] == list(range(1, 11))


def test_find_by_brand_ignores_case(seeded_session: Session) -> None:
    cars = CarRepository(seeded_session).find_by_brand("  TOYOTA ")

    assert [car.model for car in cars] == ["Corolla", "RAV4", "Camry"]


def test_find_by_unknown_brand_returns_empty_list(seeded_session: Session) -> None:
    assert CarRepository(seeded_session).find_by_brand("Tesla") == []


@pytest.mark.parametrize(
    ("min_year", "max_year", "expected_ids"),
    [
        (2016, 2019, [7, 10, 9, 1, 4, 8]),
        (2021, 2021, [2]),
        (2023, 2026, []),
    ],
    ids=["range", "one-year", "empty"],
)
def test_filter_by_year(
    seeded_session: Session, min_year: int, max_year: int, expected_ids: list[int]
) -> None:
    cars = CarRepository(seeded_session).filter_by_year(min_year, max_year)

    assert [car.id for car in cars] == expected_ids


def test_complex_filter_combines_conditions(seeded_session: Session) -> None:
    cars = CarRepository(seeded_session).find(min_year=2016, max_price=700_000, max_mileage=120_000)

    assert [car.id for car in cars] == [7, 1, 4]


def test_complex_filter_by_brand(seeded_session: Session) -> None:
    cars = CarRepository(seeded_session).find(brand="bmw", max_price=1_000_000)

    assert [car.model for car in cars] == ["320i"]


def test_sorting_by_price_descending(seeded_session: Session) -> None:
    cars = CarRepository(seeded_session).get_all(order_by="price", descending=True)

    assert [car.id for car in cars][:3] == [5, 2, 8]


def test_pagination_returns_pages_without_overlap(seeded_session: Session) -> None:
    repository = CarRepository(seeded_session)

    pages = [repository.get_page(page, 4, "mileage") for page in (1, 2, 3)]

    assert [len(page) for page in pages] == [4, 4, 2]
    assert [car.id for page in pages for car in page] == [
        car.id for car in repository.get_all("mileage")
    ]


@pytest.mark.parametrize(("page", "page_size"), [(0, 3), (1, 0)])
def test_pagination_rejects_non_positive_values(
    seeded_session: Session, page: int, page_size: int
) -> None:
    with pytest.raises(ValueError, match="додатними"):
        CarRepository(seeded_session).get_page(page, page_size)


def test_join_returns_manufacturer_country(seeded_session: Session) -> None:
    rows = CarRepository(seeded_session).list_with_manufacturer()

    assert rows[0] == (1, "Toyota", "Corolla", "Японія", 2018)
    assert len(rows) == 10


# --- Update ---


def test_update_price(seeded_session: Session) -> None:
    updated = CarRepository(seeded_session).update_price(1, 499_000)

    assert updated is not None
    assert updated.price == 499_000


def test_update_mileage(seeded_session: Session) -> None:
    updated = CarRepository(seeded_session).update_mileage(1, 90_000)

    assert updated is not None
    assert updated.mileage == 90_000


def test_update_missing_car_returns_none(seeded_session: Session) -> None:
    repository = CarRepository(seeded_session)

    assert repository.update_price(999, 1.0) is None
    assert repository.update_mileage(999, 1) is None


def test_update_manufacturer_country(seeded_session: Session) -> None:
    repository = ManufacturerRepository(seeded_session)

    updated = repository.update_country(1, "Японія (Айті)")

    assert updated is not None and updated.country == "Японія (Айті)"
    assert repository.update_country(999, "—") is None


# --- Delete ---


def test_delete_car(seeded_session: Session) -> None:
    repository = CarRepository(seeded_session)

    assert repository.delete(6) is True
    assert repository.get_by_id(6) is None
    assert repository.delete(6) is False


def test_delete_manufacturer_cascades_to_cars(seeded_session: Session) -> None:
    manufacturers = ManufacturerRepository(seeded_session)
    bmw = manufacturers.get_by_name("BMW")
    assert bmw is not None

    assert manufacturers.delete(bmw.id) is True

    assert CarRepository(seeded_session).find_by_brand("BMW") == []
    assert len(CarRepository(seeded_session).get_all()) == 8
    assert manufacturers.delete(bmw.id) is False


# --- Relationship manufacturer → cars ---


def test_manufacturer_relationship_lists_its_cars(seeded_session: Session) -> None:
    skoda = ManufacturerRepository(seeded_session).get_by_name("Skoda")

    assert skoda is not None
    assert sorted(car.model for car in skoda.cars) == ["Fabia", "Octavia"]
    assert all(car.manufacturer is skoda for car in skoda.cars)


def test_repr_shows_key_fields(seeded_session: Session) -> None:
    car = CarRepository(seeded_session).get_by_id(1)

    assert car is not None
    assert repr(car) == "Car(id=1, model='Corolla', year=2018)"
    assert repr(car.manufacturer) == "Manufacturer(id=1, name='Toyota', country='Японія')"


def test_manufacturers_are_sorted_by_name(seeded_session: Session) -> None:
    names = [item.name for item in ManufacturerRepository(seeded_session).get_all()]

    assert names == ["BMW", "Renault", "Skoda", "Toyota", "Volkswagen"]


# --- Constraints: UNIQUE, CHECK, FOREIGN KEY ---


def test_duplicate_vin_is_rejected(seeded_session: Session, make_db_car: MakeCar) -> None:
    repository = CarRepository(seeded_session)

    with pytest.raises(DatabaseConstraintError, match="UNIQUE constraint failed: cars.vin"):
        repository.add(make_db_car(1, model="Yaris", vin="JTDBR32E720000001"))

    assert len(repository.get_all()) == 10


def test_cars_without_vin_are_allowed(session: Session, make_db_car: MakeCar) -> None:
    toyota = ManufacturerRepository(session).add("Toyota", "Японія")
    repository = CarRepository(session)

    repository.add(make_db_car(toyota.id))
    repository.add(make_db_car(toyota.id, model="Camry"))

    assert len(repository.get_all()) == 2


def test_duplicate_manufacturer_name_is_rejected(seeded_session: Session) -> None:
    with pytest.raises(
        DatabaseConstraintError, match="UNIQUE constraint failed: manufacturers.name"
    ):
        ManufacturerRepository(seeded_session).add("Toyota", "Японія")


@pytest.mark.parametrize(
    ("field", "value", "constraint"),
    [
        ("year", 1949, "ck_cars_year"),
        ("year", 2027, "ck_cars_year"),
        ("price", 0, "ck_cars_price"),
        ("mileage", -1, "ck_cars_mileage"),
    ],
)
def test_check_constraints_reject_invalid_car(
    session: Session, make_db_car: MakeCar, field: str, value: int, constraint: str
) -> None:
    toyota = ManufacturerRepository(session).add("Toyota", "Японія")

    with pytest.raises(DatabaseConstraintError, match=constraint):
        CarRepository(session).add(make_db_car(toyota.id, **{field: value}))


@pytest.mark.parametrize("year", [1950, 2026])
def test_check_constraint_accepts_boundary_years(
    session: Session, make_db_car: MakeCar, year: int
) -> None:
    toyota = ManufacturerRepository(session).add("Toyota", "Японія")

    assert CarRepository(session).add(make_db_car(toyota.id, year=year)).year == year


def test_invalid_price_update_keeps_old_price(seeded_session: Session) -> None:
    repository = CarRepository(seeded_session)

    with pytest.raises(DatabaseConstraintError, match="ck_cars_price"):
        repository.update_price(3, -5)

    car = repository.get_by_id(3)
    assert car is not None and car.price == 380_000


def test_foreign_key_is_enforced(session: Session, make_db_car: MakeCar) -> None:
    with pytest.raises(DatabaseConstraintError, match="FOREIGN KEY constraint failed"):
        CarRepository(session).add(make_db_car(manufacturer_id=99))
