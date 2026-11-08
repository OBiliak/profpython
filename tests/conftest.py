"""Shared pytest fixtures of the car catalog test suite (laboratory works 6–8)."""

import logging
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from car_catalog.api import app, get_http_client, get_session
from car_catalog.domain.models import Car, Vehicle
from car_catalog.domain.services import CatalogService, MemoryLogger
from car_catalog.domain.value_objects import Mileage, Money
from car_catalog.importer.validators import ValidationPolicy
from car_catalog.persistence.database import create_database_engine, create_session_factory
from car_catalog.persistence.models import Base
from car_catalog.persistence.models import Car as CarRecord
from car_catalog.persistence.seed import seed_catalog

CSV_HEADER = "vehicle_id,brand,model,year,price,mileage"

VARIANT_ROWS = (
    (1, "Toyota", "Corolla", 2018, 520_000, 85_000),
    (2, "Toyota", "RAV4", 2021, 1_150_000, 32_000),
    (4, "Skoda", "Octavia", 2019, 610_000, 67_000),
    (5, "BMW", "X5", 2020, 1_890_000, 54_000),
    (6, "Tesla", "Model 3", 2022, 1_450_000, 28_000),
)


class FakeVehicleRepository:
    """Fake repository: a working in-memory storage written only for tests."""

    def __init__(self) -> None:
        self.items: dict[int, Vehicle] = {}

    def add(self, item: Vehicle) -> None:
        """Store a vehicle by ID."""
        self.items[item.id] = item

    def remove(self, item_id: int) -> None:
        """Delete a vehicle by ID."""
        del self.items[item_id]

    def get(self, item_id: int) -> Vehicle:
        """Return a vehicle by ID."""
        return self.items[item_id]

    def all(self) -> list[Vehicle]:
        """Return all vehicles."""
        return list(self.items.values())


@pytest.fixture(autouse=True)
def restore_logging() -> Iterator[None]:
    """Restore the root logger after every test (setup before yield, teardown after)."""
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    yield
    for handler in root.handlers:
        if handler not in handlers:
            handler.close()
    root.handlers, root.level = handlers, level


@pytest.fixture(scope="session")
def variant_rows() -> tuple[tuple[int, str, str, int, int, int], ...]:
    """Return the vehicles of variant 5 (created once per test session)."""
    return VARIANT_ROWS


@pytest.fixture
def make_car() -> Callable[..., Car]:
    """Return a factory that creates a Car with default valid fields."""

    def factory(
        vehicle_id: int = 1,
        brand: str = "Toyota",
        model: str = "Corolla",
        year: int = 2018,
        price: float = 520_000,
        mileage: int = 85_000,
    ) -> Car:
        return Car(vehicle_id, brand, model, year, Money(price), Mileage(mileage))

    return factory


@pytest.fixture
def cars(
    make_car: Callable[..., Car], variant_rows: tuple[tuple[int, str, str, int, int, int], ...]
) -> list[Car]:
    """Return five valid cars of variant 5."""
    return [make_car(*row) for row in variant_rows]


@pytest.fixture
def repository() -> FakeVehicleRepository:
    """Return an empty fake repository."""
    return FakeVehicleRepository()


@pytest.fixture
def logger() -> MemoryLogger:
    """Return a logger that keeps messages in memory."""
    return MemoryLogger()


@pytest.fixture
def catalog_service(
    repository: FakeVehicleRepository, logger: MemoryLogger, cars: list[Car]
) -> CatalogService:
    """Return a catalog service filled with the cars of variant 5."""
    service = CatalogService(repository, repository, logger)
    for car in cars:
        service.add_vehicle(car)
    return service


@pytest.fixture
def empty_service(repository: FakeVehicleRepository, logger: MemoryLogger) -> CatalogService:
    """Return a catalog service without vehicles."""
    return CatalogService(repository, repository, logger)


@pytest.fixture
def policy() -> ValidationPolicy:
    """Return the validation policy with the year range from config.yaml."""
    return ValidationPolicy(min_year=1950, max_year=2026)


@pytest.fixture
def write_csv(tmp_path: Path) -> Callable[..., Path]:
    """Return a factory that writes CSV lines of vehicles into tmp_path."""

    def factory(*lines: str, name: str = "vehicles.csv") -> Path:
        path = tmp_path / name
        path.write_text("\n".join([CSV_HEADER, *lines]) + "\n", encoding="utf-8")
        return path

    return factory


@pytest.fixture
def config_file(tmp_path: Path, write_csv: Callable[..., Path]) -> Path:
    """Create config.yaml and an input CSV in tmp_path and return the config path."""
    write_csv(
        "1,Toyota,Corolla,2018,520000,85000",
        "5,BMW,X5,2020,1890000,54000",
        "8,,Passat,2017,450000,110000",
        "17,Peugeot,308,2020,520000,39000",
        name="input.csv",
    )
    path = tmp_path / "config.yaml"
    path.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "input:",
                "  path: input.csv",
                "output:",
                "  path: output/vehicles.json",
                "  errors_path: output/invalid.csv",
                "  summary_path: output/summary.json",
                "  backup: false",
                "validation:",
                "  years: {min: 1950, max: 2026}",
                "filter:",
                "  price: {min: 0, max: 2000000}",
                "processing:",
                "  skip_invalid: true",
                "  progress_every: 100",
                "logging:",
                "  level: INFO",
                "  path: logs/test.log",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


# --- Test database of laboratory work 7: a separate SQLite file in tmp_path for every test ---


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    """Path of the test database file (never the working car_catalog.db)."""
    return tmp_path / "test_catalog.db"


@pytest.fixture
def db_engine(database_path: Path) -> Iterator[Engine]:
    """Engine of the test database with all tables (setup), disposed after the test (teardown)."""
    engine = create_database_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def session(db_engine: Engine) -> Iterator[Session]:
    """Session of the empty test database."""
    with create_session_factory(db_engine)() as db_session:
        yield db_session


@pytest.fixture
def seeded_session(session: Session) -> Session:
    """Session of the test database with 5 manufacturers and 10 cars of laboratory works 1–2."""
    seed_catalog(session)
    return session


@pytest.fixture
def make_db_car() -> Callable[..., CarRecord]:
    """Factory of ORM cars with default valid fields."""

    def factory(
        manufacturer_id: int,
        model: str = "Corolla",
        year: int = 2018,
        price: float = 520_000,
        mileage: int = 85_000,
        vin: str | None = None,
    ) -> CarRecord:
        return CarRecord(
            model=model, year=year, price=price, mileage=mileage, vin=vin, manufacturer_id=manufacturer_id
        )

    return factory


# --- REST API of laboratory work 8: the app with the test database instead of car_catalog.db ---


@pytest.fixture
def api_client(seeded_session: Session, db_engine: Engine) -> Iterator[TestClient]:
    """TestClient of the API whose sessions use the test database with the demo cars."""
    session_factory = create_session_factory(db_engine)

    def test_session() -> Iterator[Session]:
        with session_factory() as db_session:
            yield db_session

    asgi_client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides[get_session] = test_session
    app.dependency_overrides[get_http_client] = lambda: asgi_client
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
