"""Demonstration of the object-oriented car catalog with type hints (laboratory work 4)."""

from dataclasses import FrozenInstanceError

from car_catalog.domain.dto import VehiclePayload, vehicle_from_payload, vehicle_to_payload
from car_catalog.domain.exceptions import CatalogError
from car_catalog.domain.models import Car, ElectricCar, Vehicle
from car_catalog.domain.protocols import Describable
from car_catalog.domain.repositories import Repository
from car_catalog.domain.services import CatalogService, ServiceContainer
from car_catalog.domain.specifications import (
    BrandSpecification,
    MaxPriceSpecification,
    YearRangeSpecification,
)
from car_catalog.domain.statistics import average, largest, smallest
from car_catalog.domain.value_objects import Mileage, Money


def create_vehicles() -> list[Vehicle]:
    """Return demo vehicles of variant 5."""
    return [
        Car(1, "Toyota", "Corolla", 2018, Money(520_000), Mileage(85_000)),
        Car(2, "Toyota", "RAV4", 2021, Money(1_150_000), Mileage(32_000), "кросовер"),
        Car(3, "Volkswagen", "Golf", 2015, Money(380_000), Mileage(142_000), "хетчбек"),
        Car(4, "Skoda", "Octavia", 2019, Money(610_000), Mileage(67_000)),
        Car(5, "BMW", "X5", 2020, Money(1_890_000), Mileage(54_000), "кросовер"),
        ElectricCar(6, "Tesla", "Model 3", 2022, Money(1_450_000), Mileage(28_000), 75, 510),
        ElectricCar(7, "Nissan", "Leaf", 2019, Money(560_000), Mileage(41_000), 40, 270),
    ]


def print_vehicles(title: str, vehicles: list[Vehicle]) -> None:
    """Print a title and a list of vehicles."""
    print(f"\n{title}")
    if not vehicles:
        print("  автомобілів не знайдено")
    for vehicle in vehicles:
        print(f"  {vehicle}")


def show_value_objects() -> None:
    """Show immutable value objects, arithmetic dunders and total_ordering."""
    print("\n--- Value objects ---")
    price = Money(520_000)
    extra = Money(15_500)
    print(f"Money + Money: {price} + {extra} = {price + extra}")
    print(f"Money / 2: {price / 2}")
    print(f"Порівняння (total_ordering): {price} >= {extra} -> {price >= extra}")
    print(f"Mileage + Mileage: {Mileage(85_000) + Mileage(1_200)}")
    print(f"Однакові value objects рівні: {Money(100) == Money(100)}")
    try:
        price.amount = 1  # type: ignore[misc]
    except FrozenInstanceError:
        print("Зміна frozen Money -> FrozenInstanceError")
    try:
        Money(100) + Money(100, "USD")
    except CatalogError as error:
        print(f"Money(100 грн) + Money(100 USD) -> {error}")


def show_entities(service: CatalogService) -> None:
    """Add vehicles through the service and show properties and polymorphism."""
    print("\n--- Domain entities та service layer ---")
    for vehicle in create_vehicles():
        service.add_vehicle(vehicle)
    try:
        service.add_vehicle(Car(1, "Audi", "A4", 2017, Money(700_000), Mileage(90_000)))
    except CatalogError as error:
        print(f"Повторний ID 1 -> {type(error).__name__}: {error}")

    corolla = service.get_vehicle(1)
    print(f"\nrepr(): {corolla!r}")
    print(f"str():  {corolla}")
    print(f"property age: {corolla.age} р., property id: {corolla.id}")
    corolla.price = Money(505_000)
    print(f"Нова ціна через setter: {corolla.price}")
    try:
        corolla.price = Money(0)
    except CatalogError as error:
        print(f"Ціна 0 грн -> {error}")
    try:
        service.get_vehicle(99)
    except CatalogError as error:
        print(f"ID 99 -> {type(error).__name__}: {error}")

    print("\nPolymorphism: kind() для кожного об'єкта")
    for vehicle in service.search(YearRangeSpecification(2019, 2022)):
        name = f"{vehicle.brand} {vehicle.model}"
        print(f"  {name:<14} {type(vehicle).__name__:<11} -> {vehicle.kind()}")


def show_catalog(service: CatalogService) -> None:
    """Show dunder methods of the custom collection VehicleCatalog."""
    print("\n--- VehicleCatalog: dunder methods ---")
    catalog = service.build_catalog("Автосалон «Варіант 5»")
    print(f"len(catalog): {len(catalog)}")
    print(f"catalog[0]: {catalog[0]!r}")
    print(f"catalog[-1].brand: {catalog[-1].brand}")
    print(f"6 in catalog: {6 in catalog}, 42 in catalog: {42 in catalog}")
    print(f"service.get_vehicle(5) in catalog: {service.get_vehicle(5) in catalog}")
    print(f"for vehicle in catalog: {[vehicle.model for vehicle in catalog]}")


def show_search(service: CatalogService) -> None:
    """Show search by brand, model, year and combined specifications."""
    print("\n--- Пошук (VehicleSpecification) ---")
    print_vehicles("Марка «toyota»:", service.find_by_brand("toyota"))
    print_vehicles("Модель містить «model»:", service.find_by_model("model"))
    print_vehicles("Роки 2019–2021:", service.filter_by_year(2019, 2021))
    criteria = YearRangeSpecification(2018) & MaxPriceSpecification(Money(700_000))
    print_vehicles("Від 2018 року & ціна до 700000 грн:", service.search(criteria))
    is_bmw = BrandSpecification("BMW")
    bmw = service.get_vehicle(5)
    print(f"\nСпецифікація як функція (__call__): is_bmw(ID 5) -> {is_bmw(bmw)}")


def show_statistics(service: CatalogService) -> None:
    """Show the most expensive vehicle, the average price and the lowest mileage."""
    print("\n--- Статистика ---")
    summary = service.summary()
    print(f"Кількість: {summary.count}")
    print(f"Найдорожчий: {summary.most_expensive}")
    print(f"Середня ціна: {summary.average_price}")
    print(f"Мінімальний пробіг: {summary.lowest_mileage}")


def show_payloads(service: CatalogService) -> None:
    """Show TypedDict payloads and the factory of domain objects."""
    print("\n--- TypedDict payload -> domain object ---")
    payloads: list[VehiclePayload] = [
        {"id": 8, "kind": "car", "brand": "Renault", "model": "Logan",
         "year": 2012, "price": 210_000, "mileage": 198_000},
        {"id": 9, "kind": "electric", "brand": "Hyundai", "model": "Kona Electric",
         "year": 2021, "price": 890_000, "mileage": 36_000, "battery_kwh": 64, "range_km": 450},
        {"id": 10, "kind": "electric", "brand": "Renault", "model": "Zoe",
         "year": 2020, "price": 430_000, "mileage": 52_000},
        {"id": 11, "kind": "truck", "brand": "MAN", "model": "TGX",
         "year": 2016, "price": 1_300_000, "mileage": 610_000},
    ]
    for payload in payloads:
        try:
            vehicle = vehicle_from_payload(payload)
        except CatalogError as error:
            print(f"payload ID {payload['id']} -> помилка: {error}")
            continue
        service.add_vehicle(vehicle)
        print(f"payload ID {payload['id']} -> {vehicle!r}")
    print(f"Назад у payload: {vehicle_to_payload(service.get_vehicle(9))}")


def show_protocols_and_generics(container: ServiceContainer) -> None:
    """Show runtime_checkable Protocol, generic service and constrained TypeVar."""
    print("\n--- Protocol, Generic, TypeVar ---")
    tesla = container.repository.get(6)
    print(f"isinstance(tesla, Describable): {isinstance(tesla, Describable)}")
    print(f"isinstance(Money(1), Describable): {isinstance(Money(1), Describable)}")
    print(f"isinstance(repository, Repository): {isinstance(container.repository, Repository)}")

    queries = container.query_service()
    electric = queries.find(lambda vehicle: isinstance(vehicle, ElectricCar))
    print(f"QueryService[Vehicle].count(): {queries.count()}")
    print(f"QueryService[Vehicle].find(електромобілі): {[repr(v) for v in electric]}")
    print(f"QueryService[Vehicle].first(BMW): {queries.first(BrandSpecification('BMW'))!r}")

    years = [vehicle.year for vehicle in container.repository.all()]
    prices = [float(vehicle.price.amount) for vehicle in container.repository.all()]
    print(f"smallest(years: list[int]) -> {smallest(years)}")
    print(f"largest(prices: list[float]) -> {largest(prices)}")
    print(f"average(years) -> {average(years):.1f}")


def show_unit_of_work(container: ServiceContainer, service: CatalogService) -> None:
    """Show commit and rollback of the unit of work."""
    print("\n--- Unit of work ---")
    with container.unit_of_work() as unit:
        unit.register_new(Car(12, "Mazda", "CX-5", 2020, Money(980_000), Mileage(47_000)))
        unit.register_new(Car(13, "Kia", "Sportage", 2022, Money(1_050_000), Mileage(19_000)))
        print(f"commit(): збережено {unit.commit()}, у каталозі {len(container.repository)}")
    try:
        with container.unit_of_work() as unit:
            unit.register_new(Car(14, "Ford", "Focus", 2016, Money(350_000), Mileage(120_000)))
            unit.register_new(Car(2, "Ford", "Kuga", 2019, Money(720_000), Mileage(70_000)))
            unit.commit()
    except CatalogError as error:
        print(f"commit() з повторним ID -> {error}")
    saved = container.repository.find(14) is not None
    print(f"Після rollback у каталозі {len(container.repository)}, ID 14 збережено: {saved}")
    service.remove_vehicle(13)
    print(f"Після remove_vehicle(13): {len(container.repository)}")


def main() -> None:
    """Run the demonstration of laboratory work 4."""
    print("=== Каталог автомобілів: ООП і типізація (лабораторна робота №4, варіант 5) ===")
    container = ServiceContainer()
    service = container.catalog_service()
    show_value_objects()
    show_entities(service)
    show_catalog(service)
    show_search(service)
    show_statistics(service)
    show_payloads(service)
    show_protocols_and_generics(container)
    show_unit_of_work(container, service)


if __name__ == "__main__":
    main()
