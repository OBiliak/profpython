"""Integration tests: catalog import → filter → JSON export → read back."""

import json
from collections.abc import Callable
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from car_catalog.catalog_flow import export_vehicles, load_catalog
from car_catalog.domain.services import CatalogService
from car_catalog.domain.vehicle_info import AsyncVehicleInfoService
from car_catalog.importer.validators import ValidationPolicy

pytestmark = pytest.mark.integration


def test_import_filter_export_flow(
    tmp_path: Path, config_file: Path, empty_service: CatalogService, policy: ValidationPolicy
) -> None:
    load_catalog(tmp_path / "input.csv", policy, empty_service)
    selected = empty_service.filter_by_year(2019, 2022)
    output = tmp_path / "out" / "catalog.json"

    count = export_vehicles(selected, output)

    data = json.loads(output.read_text(encoding="utf-8"))
    assert count == 2
    assert [item["model"] for item in data] == ["X5", "308"]
    assert data[0]["price"] == pytest.approx(1_890_000)


@pytest.mark.asyncio
async def test_async_info_for_filtered_vehicles(
    write_csv: Callable[..., Path], empty_service: CatalogService, policy: ValidationPolicy
) -> None:
    path = write_csv("5,BMW,X5,2020,1890000,54000", "6,Tesla,Model 3,2022,1450000,28000")
    load_catalog(path, policy, empty_service)
    client = AsyncMock()
    client.fetch_info.side_effect = [
        {"country": "Німеччина"},
        {"country": "США"},
    ]
    service = AsyncVehicleInfoService(client)

    countries = [await service.get_country(car) for car in empty_service.filter_by_year(2020)]

    assert countries == ["Німеччина", "США"]
    assert client.fetch_info.await_count == 2
