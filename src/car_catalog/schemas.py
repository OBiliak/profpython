"""Pydantic schemas of the REST API: request bodies, responses and validation rules."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from car_catalog.persistence.models import MAX_YEAR, MIN_YEAR

VIN_PATTERN = r"^[A-HJ-NPR-Z0-9]{17}$"


class CarCreate(BaseModel):
    """Body of POST /cars."""

    manufacturer_id: int = Field(gt=0, examples=[1])
    model: str = Field(min_length=1, max_length=100, examples=["Prius"])
    year: int = Field(ge=MIN_YEAR, le=MAX_YEAR, examples=[2020])
    price: float = Field(gt=0, examples=[720000])
    mileage: int = Field(ge=0, examples=[45000])
    vin: str | None = Field(default=None, pattern=VIN_PATTERN, examples=["JTDKN3DU0A0000011"])


class CarUpdate(BaseModel):
    """Body of PATCH /cars/{car_id}: a new price and/or a new mileage."""

    price: float | None = Field(default=None, gt=0, examples=[505000])
    mileage: int | None = Field(default=None, ge=0, examples=[90000])

    @model_validator(mode="after")
    def check_not_empty(self) -> "CarUpdate":
        """At least one field must be given."""
        if self.price is None and self.mileage is None:
            raise ValueError("Потрібно передати price або mileage")
        return self


class CarRead(BaseModel):
    """Car in responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    brand: str
    model: str
    year: int
    price: float
    mileage: int
    vin: str | None
    manufacturer_id: int


class ManufacturerRead(BaseModel):
    """Manufacturer in responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    country: str


class CatalogStatistics(BaseModel):
    """Statistics of laboratory work 1: the most expensive car, average price, the lowest mileage."""

    count: int
    average_price: float
    most_expensive: CarRead | None
    lowest_mileage: CarRead | None


class BatchRequest(BaseModel):
    """Body of POST /cars/batch: IDs of a group of cars."""

    car_ids: list[int] = Field(min_length=1, max_length=50, examples=[[1, 2, 5, 999]])


class BatchError(BaseModel):
    """A car of the group that could not be loaded."""

    car_id: int
    error: str


class BatchResult(BaseModel):
    """Result of POST /cars/batch."""

    cars: list[CarRead]
    errors: list[BatchError]
    max_concurrency: int


class HealthResponse(BaseModel):
    """Answer of GET /health: the service and its database work."""

    status: Literal["ok"]
    environment: str
    version: str
    database: Literal["ok"]


class ErrorResponse(BaseModel):
    """Structured error of the API."""

    error: str
    detail: str
