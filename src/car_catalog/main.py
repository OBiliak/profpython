"""Entry point: the car catalog with a SQLite database (laboratory work 7, variant 5)."""

from pathlib import Path

from sqlalchemy.orm import Session

from car_catalog.persistence.database import (
    DATABASE_PATH,
    create_database_engine,
    create_session_factory,
)
from car_catalog.persistence.dbapi import count_cars_by_country, find_cars_by_manufacturer
from car_catalog.persistence.exceptions import DatabaseConstraintError, PriceUpdateError
from car_catalog.persistence.migrations import current_revision, upgrade_database
from car_catalog.persistence.models import Car
from car_catalog.persistence.repositories import CarRepository, ManufacturerRepository
from car_catalog.persistence.seed import seed_catalog
from car_catalog.persistence.services import CarCatalogService, update_prices_for_manufacturer


def show_cars(title: str, cars: list[Car]) -> None:
    """Print a list of cars with a title."""
    print(f"\n{title}: {len(cars)}")
    for car in cars:
        print(f"  {car.id:>2}: {car.describe()}")


def show_lab1_functions(service: CarCatalogService) -> None:
    """Search, filter and statistics of laboratory work 1, now as SQL queries."""
    show_cars("Пошук за маркою «Toyota»", service.find_by_brand("Toyota"))
    show_cars("Фільтр за роком випуску 2016–2019", service.filter_by_year(2016, 2019))
    most_expensive = service.get_most_expensive()
    lowest_mileage = service.get_lowest_mileage()
    print("\n--- Статистика (SQL: ORDER BY ... LIMIT 1, AVG, COUNT, SUM) ---")
    if most_expensive is not None and lowest_mileage is not None:
        print(f"Найдорожчий: {most_expensive.describe()}")
        print(f"Мінімальний пробіг: {lowest_mileage.describe()}")
    print(f"Середня ціна: {service.get_average_price():.2f} грн")
    print(f"Кількість автомобілів: {service.count_cars()}")
    print(f"Загальна вартість: {service.get_total_value():.2f} грн")
    print("\n--- За виробниками (JOIN + GROUP BY) ---")
    for row in service.statistics_by_manufacturer():
        print(f"  {row.name:<10} авто: {row.car_count}  середня: {row.average_price:.2f}  "
              f"сума: {row.total_price:.2f}")


def show_crud(session: Session) -> None:
    """Create, read, update (price and mileage) and delete a car; delete a manufacturer with cascade."""
    manufacturers = ManufacturerRepository(session)
    cars = CarRepository(session)
    print("\n--- CRUD ---")
    renault = manufacturers.get_by_name("Renault")
    assert renault is not None
    car = cars.add(Car(model="Duster", year=2022, price=780_000, mileage=15_000,
                       vin="VF1HJD20X0C000011", manufacturer_id=renault.id))
    print(f"Create: ID {car.id} — {car.describe()}")
    loaded = cars.get_by_id(car.id)
    print(f"Read:   ID {car.id} — {loaded.describe() if loaded else 'не знайдено'}")
    cars.update_price(car.id, 765_000)
    updated = cars.update_mileage(car.id, 18_500)
    print(f"Update: ID {car.id} — {updated.describe() if updated else 'не знайдено'}")
    print(f"Delete: ID {car.id} — {cars.delete(car.id)}; повторне читання: {cars.get_by_id(car.id)}")

    tesla = manufacturers.add("Tesla", "США")
    cars.add(Car(model="Model 3", year=2022, price=1_450_000, mileage=28_000,
                 vin="5YJ3E7EB0NF000012", manufacturer_id=tesla.id))
    print(f"Новий виробник: {tesla.name} ({tesla.country}), авто: {len(tesla.cars)}")
    manufacturers.update_country(tesla.id, "США (Каліфорнія)")
    print(f"Зміна країни: {tesla.name} — {tesla.country}")
    manufacturers.delete(tesla.id)
    print(f"Видалення Tesla (ON DELETE CASCADE): авто Tesla в БД — {len(cars.find_by_brand('Tesla'))}")


def show_queries(session: Session) -> None:
    """JOIN, sorting, pagination and a complex filter."""
    cars = CarRepository(session)
    print("\n--- JOIN cars + manufacturers ---")
    for car_id, brand, model, country, year in cars.list_with_manufacturer()[:4]:
        print(f"  {car_id:>2}: {brand} {model} ({country}), {year}")
    print("  ...")
    for page in (1, 2):
        show_cars(f"Сторінка {page} (по 3, за ціною спадно)", cars.get_page(page, 3, "price", descending=True))
    show_cars("Складний фільтр: рік ≥ 2016, ціна ≤ 700000, пробіг ≤ 120000",
              cars.find(min_year=2016, max_price=700_000, max_mileage=120_000))


def show_dbapi() -> None:
    """Parameterized queries through sqlite3 (DB-API) without ORM."""
    print("\n--- DB-API (sqlite3), parameterized query: WHERE lower(manufacturers.name) = lower(?) ---")
    for brand in ("Skoda", "Toyota' OR '1'='1"):
        rows = find_cars_by_manufacturer(DATABASE_PATH, brand)
        print(f"Параметр {brand!r}: {len(rows)} рядк.")
        for row in rows:
            print(f"  {row}")
    print(f"COUNT за країнами (GROUP BY): {count_cars_by_country(DATABASE_PATH)}")


def show_transactions(session: Session) -> None:
    """Bulk price update of one manufacturer: commit on success, rollback on incorrect data."""
    service = CarCatalogService(session)
    print("\n--- Транзакція: масове оновлення цін виробника ---")
    new_prices: dict[int, float] = {1: 505_000, 2: 1_120_000, 8: 955_000}
    count = update_prices_for_manufacturer(session, "Toyota", new_prices)
    print(f"Toyota {new_prices}: commit, оновлено {count}")
    show_cars("Toyota після commit", service.find_by_brand("Toyota"))

    before = [car.price for car in service.find_by_brand("Volkswagen")]
    try:
        update_prices_for_manufacturer(session, "Volkswagen", {3: 365_000, 9: -1})
    except PriceUpdateError as error:
        print(f"\nVolkswagen {{3: 365000, 9: -1}}: rollback — {error}")
    after = [car.price for car in service.find_by_brand("Volkswagen")]
    print(f"Ціни Volkswagen до: {before}, після rollback: {after}")
    try:
        update_prices_for_manufacturer(session, "Skoda", {4: 600_000, 5: 1_800_000})
    except PriceUpdateError as error:
        print(f"Skoda {{4: 600000, 5: 1800000}}: rollback — {error}")


def show_constraints(session: Session) -> None:
    """UNIQUE VIN, CHECK and FOREIGN KEY are checked by SQLite itself."""
    cars = CarRepository(session)
    print("\n--- Обмеження БД (IntegrityError → DatabaseConstraintError) ---")
    attempts = {
        "Дублікат VIN JTDBR32E720000001": Car(model="Yaris", year=2020, price=450_000, mileage=40_000,
                                             vin="JTDBR32E720000001", manufacturer_id=1),
        "Рік 1949": Car(model="Classic", year=1949, price=900_000, mileage=1_000, manufacturer_id=1),
        "Неіснуючий manufacturer_id 99": Car(model="Ghost", year=2020, price=500_000, mileage=10,
                                             manufacturer_id=99),
    }
    for title, car in attempts.items():
        try:
            cars.add(car)
        except DatabaseConstraintError as error:
            print(f"  {title}: {error}")
    try:
        cars.update_mileage(6, -100)
    except DatabaseConstraintError as error:
        print(f"  Пробіг -100 для ID 6: {error}")
    print(f"Кількість автомобілів після відхилених записів: {CarCatalogService(session).count_cars()}")


def main() -> None:
    """Recreate the database with migrations and run the scenario of laboratory work 7."""
    print("=== Каталог автомобілів: база даних SQLite (лабораторна робота №7, варіант 5) ===")
    Path(DATABASE_PATH).unlink(missing_ok=True)
    database_url = f"sqlite:///{DATABASE_PATH}"
    upgrade_database(database_url)
    engine = create_database_engine(database_url)
    print(f"БД {DATABASE_PATH} створено міграціями Alembic, ревізія: {current_revision(engine)}")
    with create_session_factory(engine)() as session:
        count = seed_catalog(session)
        print(f"Додано виробників: {len(ManufacturerRepository(session).get_all())}, автомобілів: {count}")
        service = CarCatalogService(session)
        show_cars("Усі автомобілі", CarRepository(session).get_all())
        show_lab1_functions(service)
        show_crud(session)
        show_queries(session)
        show_dbapi()
        show_transactions(session)
        show_constraints(session)
    engine.dispose()
    print("\nТести: python -m pytest -v; міграції: alembic upgrade head, alembic current")


if __name__ == "__main__":
    main()
