"""Tested car catalog scenario of laboratory work 6: python -m car_catalog.catalog_app."""

import asyncio
import sys
from pathlib import Path

from car_catalog.catalog_flow import export_vehicles, load_catalog
from car_catalog.domain.exceptions import CatalogError
from car_catalog.domain.models import Vehicle
from car_catalog.domain.repositories import InMemoryRepository
from car_catalog.domain.services import CatalogService, MemoryLogger
from car_catalog.domain.vehicle_info import (
    AsyncVehicleInfoService,
    LocalAsyncVehicleInfoClient,
    LocalVehicleInfoProvider,
    VehicleInfoError,
    VehicleInfoService,
)
from car_catalog.importer.config import load_config
from car_catalog.importer.exceptions import ApplicationError
from car_catalog.importer.logging_config import configure_console_logging
from car_catalog.importer.validators import ValidationPolicy


def show_vehicles(title: str, vehicles: list[Vehicle]) -> None:
    """Print a list of vehicles with a title."""
    print(f"\n{title}: {len(vehicles)}")
    for vehicle in vehicles:
        print(f"  {vehicle.id}: {vehicle.describe()}")


def show_statistics(service: CatalogService) -> None:
    """Print the most expensive vehicle, the average price and the lowest mileage."""
    print("\n--- Статистика каталогу ---")
    print(f"Найдорожчий: {service.most_expensive().describe()}")
    print(f"Середня ціна: {service.average_price()}")
    print(f"Мінімальний пробіг: {service.lowest_mileage().describe()}")


def show_vehicle_info(vehicles: list[Vehicle]) -> None:
    """Print countries of brands from the vehicle info service; failed requests are skipped."""
    logger = MemoryLogger()
    service = VehicleInfoService(LocalVehicleInfoProvider(), logger)
    result = service.collect_info(vehicles)
    print("\n--- External vehicle info service ---")
    for vehicle_id, info in result.items():
        print(f"  {vehicle_id}: {info.brand} {info.model} — {info.country}")
    for message in logger.messages:
        if message.startswith("пропущено"):
            print(f"  {message}")


async def show_countries_async(vehicles: list[Vehicle]) -> None:
    """Ask the asynchronous client about the countries of several vehicles."""
    service = AsyncVehicleInfoService(LocalAsyncVehicleInfoClient())
    print("\n--- Async vehicle info ---")
    for vehicle in vehicles:
        try:
            country = await service.get_country(vehicle)
        except VehicleInfoError as error:
            print(f"  {vehicle.brand} {vehicle.model}: {error}")
            continue
        print(f"  {vehicle.brand} {vehicle.model}: {country}")


def main(argv: list[str] | None = None) -> int:
    """Run the catalog scenario of laboratory work 6; return the exit code."""
    args = sys.argv[1:] if argv is None else argv
    config_path = Path(args[0]) if args else Path("config.yaml")
    configure_console_logging()
    print("=== Каталог автомобілів: сценарій, покритий тестами (лабораторна робота №6, варіант 5) ===")
    repository = InMemoryRepository[Vehicle]()
    service = CatalogService(repository, repository, MemoryLogger())
    try:
        config = load_config(config_path)
        policy = ValidationPolicy.from_config(config.validation)
        statistics, errors = load_catalog(config.input.path, policy, service)
    except (ApplicationError, CatalogError) as error:
        print(f"Помилка: {error}")
        return 1
    invalid_lines = ", ".join(str(invalid.line_number) for invalid in errors)
    print(f"\nІмпорт {config.input.path.name}: усього {statistics.total}, valid {statistics.valid}, "
          f"invalid {statistics.invalid} (рядки {invalid_lines})")

    show_vehicles("Пошук за маркою «Toyota»", service.find_by_brand("Toyota"))
    show_vehicles("Пошук за моделлю «Model»", service.find_by_model("Model"))
    selected = service.filter_by_year(2019, 2022)
    show_vehicles("Фільтр за роком випуску 2019–2022", selected)
    show_statistics(service)
    show_vehicle_info(selected)
    asyncio.run(show_countries_async(selected[:3]))

    output = config.output.path.with_name("catalog_2019_2022.json")
    count = export_vehicles(selected, output)
    print(f"\nJSON export: {count} автомобілів -> {output.as_posix()}")
    print("Тести: python -m pytest -v; coverage: python -m pytest --cov --cov-report=term-missing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
