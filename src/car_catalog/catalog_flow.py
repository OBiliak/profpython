"""Catalog flow: file import → domain catalog → filter → JSON export (laboratory work 6)."""

from pathlib import Path

from car_catalog.domain.models import Car, Vehicle
from car_catalog.domain.services import CatalogService
from car_catalog.domain.value_objects import Mileage, Money
from car_catalog.importer.exporters import export_records
from car_catalog.importer.models import InvalidRecord, VehicleRecord
from car_catalog.importer.readers import select_importer
from car_catalog.importer.services import ImportStatistics, import_vehicles
from car_catalog.importer.validators import ValidationPolicy


def record_to_car(record: VehicleRecord) -> Car:
    """Create a domain Car from a validated import record."""
    return Car(
        record.vehicle_id,
        record.brand,
        record.model,
        record.year,
        Money(record.price),
        Mileage(record.mileage),
    )


def car_to_record(vehicle: Vehicle) -> VehicleRecord:
    """Create an export record from a domain vehicle."""
    return VehicleRecord(
        vehicle_id=vehicle.id,
        brand=vehicle.brand,
        model=vehicle.model,
        year=vehicle.year,
        price=vehicle.price.amount,
        mileage=vehicle.mileage.km,
    )


def load_catalog(
    path: Path, policy: ValidationPolicy, service: CatalogService
) -> tuple[ImportStatistics, list[InvalidRecord]]:
    """Add valid vehicles from a file to the catalog; invalid rows are collected."""
    statistics = ImportStatistics()
    errors: list[InvalidRecord] = []
    records = import_vehicles(
        select_importer(path).read(path),
        policy=policy,
        skip_invalid=True,
        statistics=statistics,
        errors=errors,
    )
    for record in records:
        service.add_vehicle(record_to_car(record))
    return statistics, errors


def export_vehicles(vehicles: list[Vehicle], path: Path) -> int:
    """Export domain vehicles to a JSON or JSON Lines file atomically."""
    return export_records((car_to_record(vehicle) for vehicle in vehicles), path)
