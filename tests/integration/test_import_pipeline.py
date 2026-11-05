"""Integration tests: CSV file → reader → validation → domain catalog."""

from collections.abc import Callable
from pathlib import Path

import pytest

from car_catalog.catalog_flow import load_catalog
from car_catalog.domain.services import CatalogService
from car_catalog.importer.validators import ValidationPolicy

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_imports_variant_csv_into_catalog(
    empty_service: CatalogService, policy: ValidationPolicy
) -> None:
    statistics, errors = load_catalog(PROJECT_ROOT / "data" / "vehicles.csv", policy, empty_service)

    assert (statistics.total, statistics.valid, statistics.invalid) == (20, 12, 8)
    assert [invalid.line_number for invalid in errors] == [9, 11, 12, 13, 14, 15, 16, 17]
    assert empty_service.most_expensive().model == "S-Class"
    assert empty_service.average_price().amount == pytest.approx(1_332_916.67, abs=0.01)


def test_malformed_and_boundary_rows_do_not_stop_import(
    write_csv: Callable[..., Path], empty_service: CatalogService, policy: ValidationPolicy
) -> None:
    path = write_csv(
        "1,Toyota,Corolla,1950,520000,0",
        "2,Renault,Logan,2012,0,198000",
        "3,Audi,A4,2017,700000",
        "4,Skoda,Octavia,2026,610000,67000",
    )

    statistics, errors = load_catalog(path, policy, empty_service)

    assert statistics.valid == 2
    assert [invalid.line_number for invalid in errors] == [3, 4]
    assert [vehicle.id for vehicle in empty_service.filter_by_year(1950, 2026)] == [1, 4]
