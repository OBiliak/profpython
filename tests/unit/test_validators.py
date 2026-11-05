"""Unit tests of import record validation: boundary, invalid and malformed records."""

import pytest

from car_catalog.importer.exceptions import RecordValidationError
from car_catalog.importer.validators import ValidationPolicy

VALID_ROW = {
    "vehicle_id": "9",
    "brand": "Mercedes-Benz",
    "model": "S-Class",
    "year": "2023",
    "price": "4200000",
    "mileage": "9000",
}


def row_with(**changes: str) -> dict[str, str]:
    """Return a copy of the valid row with changed fields."""
    return {**VALID_ROW, **changes}


def test_parses_valid_record(policy: ValidationPolicy) -> None:
    record = policy.parse(VALID_ROW, line_number=10)

    assert record.vehicle_id == 9
    assert record.brand == "Mercedes-Benz"
    assert record.year == 2023
    assert record.price == pytest.approx(4_200_000.0)
    assert record.mileage == 9000


@pytest.mark.parametrize("year", ["1950", "2026"], ids=["min-year", "max-year"])
def test_accepts_boundary_years_from_config(policy: ValidationPolicy, year: str) -> None:
    assert policy.parse(row_with(year=year), line_number=2).year == int(year)


def test_accepts_zero_mileage(policy: ValidationPolicy) -> None:
    assert policy.parse(row_with(mileage="0"), line_number=2).mileage == 0


@pytest.mark.parametrize(
    ("changes", "field", "message"),
    [
        ({"brand": ""}, "brand", "Поле brand порожнє"),
        ({"year": "1949"}, "year", "year має бути в межах 1950–2026"),
        ({"year": "2027"}, "year", "year має бути в межах 1950–2026"),
        ({"year": "wrong"}, "year", "має бути цілим числом"),
        ({"price": "-210000"}, "price", "price"),
        ({"price": "0"}, "price", "price"),
        ({"mileage": "-19000"}, "mileage", "mileage не може бути від'ємним"),
        ({"vehicle_id": "0"}, "vehicle_id", "vehicle_id має бути додатним"),
        ({"vehicle_id": "abc"}, "vehicle_id", "має бути цілим числом"),
    ],
    ids=[
        "empty-brand",
        "year-below-min",
        "year-above-max",
        "year-not-number",
        "negative-price",
        "zero-price",
        "negative-mileage",
        "zero-id",
        "id-not-number",
    ],
)
def test_rejects_invalid_record(
    policy: ValidationPolicy, changes: dict[str, str], field: str, message: str
) -> None:
    with pytest.raises(RecordValidationError, match=message) as exc_info:
        policy.parse(row_with(**changes), line_number=7)

    assert exc_info.value.field == field
    assert exc_info.value.line_number == 7


def test_rejects_malformed_record_without_field(policy: ValidationPolicy) -> None:
    row = dict(VALID_ROW)
    del row["mileage"]

    with pytest.raises(RecordValidationError, match="Поле mileage порожнє"):
        policy.parse(row, line_number=17)


def test_number_error_keeps_original_cause(policy: ValidationPolicy) -> None:
    with pytest.raises(RecordValidationError) as exc_info:
        policy.parse(row_with(price="дорого"), line_number=3)

    assert isinstance(exc_info.value.__cause__, ValueError)
