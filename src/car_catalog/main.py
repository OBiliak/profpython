"""Entry point: analysis of the car catalog (laboratory work 2)."""

from car_catalog.analytics import (
    calculate_average_price,
    calculate_average_values,
    create_car_record,
    create_mileage_filter,
    create_price_filter,
    filter_cars,
    find_lowest_mileage_car,
    find_most_expensive_car,
    sort_by_price,
    sort_cars,
)
from car_catalog.config import CURRENCY
from car_catalog.data import cars
from car_catalog.decorators import operation_history
from car_catalog.processors import (
    count_cars_by_brand,
    create_car_index,
    filter_by_year,
    find_car_by_id,
    get_unique_brands,
    group_by_brand,
    group_by_brand_and_year,
)

YEAR_RANGE = (2016, 2019)


def format_car(car: dict) -> str:
    """Return one line with all fields of a car record."""
    return (
        f"{car['id']:>3}  {car['brand']:<11} {car['model']:<8} {car['year']}  "
        f"{car['price']:>11.2f} {CURRENCY}  {car['mileage']:>7} км"
    )


def print_cars(title: str, items: list[dict]) -> None:
    """Print a title and a table of car records."""
    print(f"\n{title}")
    print("-" * 64)
    if not items:
        print("Автомобілів не знайдено.")
    for car in items:
        print(format_car(car))


def print_car(title: str, car: dict | None) -> None:
    """Print a title and one car record or a message for an empty result."""
    print(f"\n{title}")
    print(format_car(car) if car else "Автомобілів не знайдено.")


def print_statistics() -> None:
    """Print unique brands, counts by brand and price statistics."""
    print(f"\nУнікальні марки: {sorted(get_unique_brands(cars))}")
    print("\nКількість автомобілів кожної марки:")
    for brand, count in count_cars_by_brand(cars).most_common():
        print(f"  {brand:<11} {count}")
    average = calculate_average_price(cars)
    print(f"Середня ціна: {average:.2f} {CURRENCY}")
    print_car("Найдорожчий автомобіль:", find_most_expensive_car(cars))
    print_car("Автомобіль із найменшим пробігом:", find_lowest_mileage_car(cars))


def print_search_and_groups() -> None:
    """Print search by ID and grouping results."""
    index = create_car_index(cars)
    print_car("Пошук за ID 8 (dict-index):", find_car_by_id(index, 8))
    print_car("Пошук за ID 99 (dict-index):", find_car_by_id(index, 99))
    print("\nГрупування за маркою (моделі):")
    for brand, items in group_by_brand(cars).items():
        print(f"  {brand:<11} {[car['model'] for car in items]}")
    print("\nВкладене групування: марка → рік → моделі:")
    for brand, years in group_by_brand_and_year(cars).items():
        print(f"  {brand:<11} {dict(sorted(years.items()))}")


def print_functional_examples() -> None:
    """Print examples of *args, **kwargs, closures and universal functions."""
    prices = (cars[0]["price"], cars[1]["price"], cars[2]["price"])
    average = calculate_average_values(*prices)
    print(f"\n*args: середня ціна перших трьох = {average:.2f} {CURRENCY}")
    record = create_car_record(
        id=11, brand="Honda", model="Civic", year=2022, price=980000.0, mileage=15000
    )
    print(f"**kwargs: створено запис {record}")
    is_affordable = create_price_filter(700000)
    is_low_mileage = create_mileage_filter(100000)
    print_cars(
        "Closure-фільтри: ціна до 700000 грн і пробіг до 100000 км:",
        filter_cars(cars, is_affordable, is_low_mileage),
    )
    print_cars("Універсальне сортування за пробігом:", sort_cars(cars, "mileage"))


def main() -> None:
    """Run the analysis of the demo car catalog."""
    print("=== Аналіз каталогу автомобілів (лабораторна робота №2, варіант 5) ===")
    print_cars("Усі автомобілі:", cars)
    print_statistics()
    print_cars("Сортування за ціною (від дешевших):", sort_by_price(cars))
    print_cars(
        f"Фільтрація за роком {YEAR_RANGE[0]}–{YEAR_RANGE[1]}:",
        filter_by_year(cars, *YEAR_RANGE),
    )
    print_search_and_groups()
    print_functional_examples()
    print("\nІсторія останніх операцій (deque, maxlen=5):")
    for label, size in operation_history:
        print(f"  {label}: кількість записів у результаті = {size}")


if __name__ == "__main__":
    main()
