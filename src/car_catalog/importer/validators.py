"""Parsing and validation of input vehicle records."""

from dataclasses import dataclass
from typing import Any

from car_catalog.importer.exceptions import RecordValidationError
from car_catalog.importer.models import ValidationConfig, VehicleRecord


def read_field(row: dict[str, Any], field: str, line_number: int) -> str:
    """Return a non-empty text value of a field."""
    value = row.get(field)
    text = "" if value is None else str(value).strip()
    if not text:
        raise RecordValidationError(f"Поле {field} порожнє", line_number=line_number, field=field)
    return text


def parse_int(row: dict[str, Any], field: str, line_number: int) -> int:
    """Convert a field to int, keeping the original error as the cause."""
    text = read_field(row, field, line_number)
    try:
        return int(text)
    except ValueError as error:
        raise RecordValidationError(
            f"Поле {field} має бути цілим числом: {text!r}",
            line_number=line_number,
            field=field,
        ) from error


def parse_float(row: dict[str, Any], field: str, line_number: int) -> float:
    """Convert a field to float, keeping the original error as the cause."""
    text = read_field(row, field, line_number)
    try:
        return float(text)
    except ValueError as error:
        raise RecordValidationError(
            f"Поле {field} має бути числом: {text!r}",
            line_number=line_number,
            field=field,
        ) from error


@dataclass(frozen=True, slots=True)
class ValidationPolicy:
    """Rules of a valid vehicle record; the year range comes from config.yaml."""

    min_year: int
    max_year: int

    @classmethod
    def from_config(cls, config: ValidationConfig) -> "ValidationPolicy":
        """Create the policy from the validation section of the configuration."""
        return cls(config.min_year, config.max_year)

    def parse(self, row: dict[str, Any], line_number: int) -> VehicleRecord:
        """Convert a raw row to a VehicleRecord or raise RecordValidationError."""
        record = VehicleRecord(
            vehicle_id=parse_int(row, "vehicle_id", line_number),
            brand=read_field(row, "brand", line_number),
            model=read_field(row, "model", line_number),
            year=parse_int(row, "year", line_number),
            price=parse_float(row, "price", line_number),
            mileage=parse_int(row, "mileage", line_number),
        )
        self.validate(record, line_number)
        return record

    def validate(self, record: VehicleRecord, line_number: int) -> None:
        """Check value ranges of a parsed record."""
        if record.vehicle_id <= 0:
            self.reject("vehicle_id має бути додатним", "vehicle_id", line_number)
        if not self.min_year <= record.year <= self.max_year:
            message = f"year має бути в межах {self.min_year}–{self.max_year}"
            self.reject(message, "year", line_number)
        if record.price <= 0:
            self.reject("price має бути більшою за нуль", "price", line_number)
        if record.mileage < 0:
            self.reject("mileage не може бути від'ємним", "mileage", line_number)

    @staticmethod
    def reject(message: str, field: str, line_number: int) -> None:
        """Raise RecordValidationError for a field."""
        raise RecordValidationError(message, line_number=line_number, field=field)
