"""REST API of the car catalog (FastAPI, laboratory work 8): uvicorn car_catalog.api:app."""

from collections.abc import Iterator

from fastapi import FastAPI
from sqlalchemy.orm import Session

from car_catalog import __version__
from car_catalog.persistence.database import SessionLocal

app = FastAPI(
    title="Car Catalog API",
    description="REST API каталогу автомобілів (лабораторна робота №8, варіант 5): cars і manufacturers.",
    version=__version__,
)


def get_session() -> Iterator[Session]:
    """Dependency: one database session per request, closed after the response."""
    with SessionLocal() as session:
        yield session


@app.get("/", tags=["service"])
async def root() -> dict[str, str]:
    """Short information about the API."""
    return {"name": "Car Catalog API", "version": __version__, "docs": "/docs"}
