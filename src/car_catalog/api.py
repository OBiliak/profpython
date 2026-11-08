"""REST API of the car catalog (FastAPI, laboratory work 8): uvicorn car_catalog.api:app."""

import asyncio
import logging
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from car_catalog import __version__
from car_catalog.config import get_settings
from car_catalog.external_api import ClientSettings, create_client, fetch_cars
from car_catalog.persistence.database import (
    create_database_engine,
    create_session_factory,
    database_url,
)
from car_catalog.persistence.exceptions import DatabaseConstraintError
from car_catalog.persistence.models import MAX_YEAR, MIN_YEAR, Car, Manufacturer
from car_catalog.persistence.repositories import CarRepository, ManufacturerRepository
from car_catalog.persistence.services import CarCatalogService
from car_catalog.schemas import (
    BatchError,
    BatchRequest,
    BatchResult,
    CarCreate,
    CarRead,
    CarUpdate,
    CatalogStatistics,
    ErrorResponse,
    HealthResponse,
    ManufacturerRead,
)

logger = logging.getLogger("car_catalog.api")


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """At startup: database engine and one shared httpx.AsyncClient; at shutdown: close both."""
    engine = create_database_engine(database_url())
    application.state.session_factory = create_session_factory(engine)
    logger.info(
        "Car Catalog API started: environment=%s, database=%s",
        get_settings().environment,
        engine.url.render_as_string(hide_password=True),  # a password in the URL is never logged
    )
    settings = ClientSettings.from_env()
    application.state.client_settings = settings
    application.state.http_client = create_client(settings)
    yield
    await application.state.http_client.aclose()
    engine.dispose()


app = FastAPI(
    lifespan=lifespan,
    title="Car Catalog API",
    description="REST API каталогу автомобілів (варіант 5): cars, manufacturers і health check.",
    version=__version__,
    openapi_tags=[
        {"name": "cars", "description": "Автомобілі: CRUD, пошук, фільтр, статистика"},
        {"name": "manufacturers", "description": "Виробники та їхні автомобілі"},
        {"name": "service", "description": "Службові endpoints"},
    ],
)

BATCH_TIMEOUT = 10.0
NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "Запис не знайдено"}
}


def get_session(request: Request) -> Iterator[Session]:
    """Dependency: one database session per request, closed after the response."""
    with request.app.state.session_factory() as session:
        yield session


def get_http_client(request: Request) -> httpx.AsyncClient:
    """Dependency: the shared AsyncClient created in lifespan."""
    client: httpx.AsyncClient = request.app.state.http_client
    return client


SessionDep = Annotated[Session, Depends(get_session)]
HttpClientDep = Annotated[httpx.AsyncClient, Depends(get_http_client)]


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, error: HTTPException) -> JSONResponse:
    """Structured error response: {"error": ..., "detail": ...}."""
    names = {
        404: "not_found",
        409: "conflict",
        422: "validation_error",
        503: "service_unavailable",
        504: "timeout",
    }
    body = ErrorResponse(error=names.get(error.status_code, "http_error"), detail=str(error.detail))
    return JSONResponse(status_code=error.status_code, content=body.model_dump())


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, error: RequestValidationError) -> JSONResponse:
    """Pydantic validation error → 422 with all messages in one line ("field: message; ...")."""
    messages = [
        f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}" for item in error.errors()
    ]
    body = ErrorResponse(error="validation_error", detail="; ".join(messages))
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=body.model_dump()
    )


@app.exception_handler(DatabaseConstraintError)
async def constraint_error_handler(
    request: Request, error: DatabaseConstraintError
) -> JSONResponse:
    """UNIQUE / CHECK / FOREIGN KEY violation in the database → 409 Conflict."""
    body = ErrorResponse(error="conflict", detail=str(error))
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=body.model_dump())


def find_car(session: Session, car_id: int) -> Car:
    """Return a car or raise 404."""
    car = CarRepository(session).get_by_id(car_id)
    if car is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Автомобіль з ID {car_id} не знайдено"
        )
    return car


def log_new_car(car_id: int, description: str) -> None:
    """Background task: write a log record after the response has been sent."""
    logger.info("Додано автомобіль %s: %s", car_id, description)


@app.get("/", tags=["service"])
async def root() -> dict[str, str]:
    """Short information about the API."""
    return {"name": "Car Catalog API", "version": __version__, "docs": "/docs"}


@app.get(
    "/health",
    tags=["service"],
    response_model=HealthResponse,
    responses={503: {"model": ErrorResponse, "description": "База даних недоступна"}},
)
def health(session: SessionDep) -> HealthResponse:
    """Health check for Docker and monitoring: the service answers and the database executes SELECT 1."""
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        logger.error("Health check failed: %s", error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="База даних недоступна"
        ) from error
    return HealthResponse(
        status="ok", environment=get_settings().environment, version=__version__, database="ok"
    )


@app.get("/cars", response_model=list[CarRead], tags=["cars"])
def list_cars(
    session: SessionDep,
    brand: Annotated[
        str | None, Query(description="Марка (виробник), без урахування регістру")
    ] = None,
    model: Annotated[str | None, Query(description="Частина назви моделі")] = None,
    min_year: Annotated[int | None, Query(ge=MIN_YEAR, le=MAX_YEAR)] = None,
    max_year: Annotated[int | None, Query(ge=MIN_YEAR, le=MAX_YEAR)] = None,
    sort_by: Literal["id", "year", "price", "mileage"] = "id",
    descending: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Car]:
    """Search by brand/model, filter by year, sorting and pagination."""
    if min_year is not None and max_year is not None and min_year > max_year:
        raise HTTPException(status_code=422, detail="min_year не може бути більшим за max_year")
    return CarRepository(session).search(
        brand, model, min_year, max_year, sort_by, descending, limit, offset
    )


@app.get("/cars/statistics", response_model=CatalogStatistics, tags=["cars"])
def car_statistics(session: SessionDep) -> CatalogStatistics:
    """The most expensive car, the average price and the car with the lowest mileage."""
    service = CarCatalogService(session)
    expensive = service.get_most_expensive()
    lowest = service.get_lowest_mileage()
    return CatalogStatistics(
        count=service.count_cars(),
        average_price=round(service.get_average_price(), 2),
        most_expensive=CarRead.model_validate(expensive) if expensive else None,
        lowest_mileage=CarRead.model_validate(lowest) if lowest else None,
    )


@app.get("/cars/{car_id}", response_model=CarRead, responses=NOT_FOUND, tags=["cars"])
def get_car(car_id: int, session: SessionDep) -> Car:
    """One car by ID."""
    return find_car(session, car_id)


@app.post(
    "/cars",
    response_model=CarRead,
    status_code=status.HTTP_201_CREATED,
    responses={**NOT_FOUND, 409: {"model": ErrorResponse, "description": "VIN вже існує"}},
    tags=["cars"],
)
def create_car(data: CarCreate, session: SessionDep, background_tasks: BackgroundTasks) -> Car:
    """Add a car; the manufacturer must exist, the VIN must be unique."""
    if ManufacturerRepository(session).get_by_id(data.manufacturer_id) is None:
        raise HTTPException(
            status_code=404, detail=f"Виробника з ID {data.manufacturer_id} не знайдено"
        )
    car = CarRepository(session).add(Car(**data.model_dump()))
    background_tasks.add_task(log_new_car, car.id, car.describe())
    return car


@app.post(
    "/cars/batch",
    response_model=BatchResult,
    responses={504: {"model": ErrorResponse, "description": "Операція не завершилася вчасно"}},
    tags=["cars"],
)
async def load_cars_batch(
    data: BatchRequest, request: Request, client: HttpClientDep
) -> BatchResult:
    """Load a group of cars concurrently through GET /cars/{id} (HTTPX, Task, gather, Semaphore, retry)."""
    settings: ClientSettings = request.app.state.client_settings
    try:
        result = await asyncio.wait_for(
            fetch_cars(client, data.car_ids, settings), timeout=BATCH_TIMEOUT
        )
    except TimeoutError as error:
        raise HTTPException(
            status_code=504, detail="Пакетне завантаження не завершилося вчасно"
        ) from error
    return BatchResult(
        cars=[CarRead(**car) for car in result.cars],
        errors=[BatchError(car_id=car_id, error=text) for car_id, text in result.errors],
        max_concurrency=result.max_concurrency,
    )


@app.patch("/cars/{car_id}", response_model=CarRead, responses=NOT_FOUND, tags=["cars"])
def update_car(car_id: int, data: CarUpdate, session: SessionDep) -> Car:
    """Change the price and/or the mileage of a car."""
    car = find_car(session, car_id)
    repository = CarRepository(session)
    if data.price is not None:
        repository.update_price(car_id, data.price)
    if data.mileage is not None:
        repository.update_mileage(car_id, data.mileage)
    return car


@app.delete(
    "/cars/{car_id}", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND, tags=["cars"]
)
def delete_car(car_id: int, session: SessionDep) -> None:
    """Delete a car."""
    find_car(session, car_id)
    CarRepository(session).delete(car_id)


@app.get("/manufacturers", response_model=list[ManufacturerRead], tags=["manufacturers"])
def list_manufacturers(session: SessionDep) -> list[Manufacturer]:
    """All manufacturers sorted by name."""
    return ManufacturerRepository(session).get_all()


@app.get(
    "/manufacturers/{manufacturer_id}/cars",
    response_model=list[CarRead],
    responses=NOT_FOUND,
    tags=["manufacturers"],
)
def manufacturer_cars(manufacturer_id: int, session: SessionDep) -> list[Car]:
    """Cars of one manufacturer (relationship manufacturer.cars)."""
    manufacturer = ManufacturerRepository(session).get_by_id(manufacturer_id)
    if manufacturer is None:
        raise HTTPException(status_code=404, detail=f"Виробника з ID {manufacturer_id} не знайдено")
    return sorted(manufacturer.cars, key=lambda car: car.id)
