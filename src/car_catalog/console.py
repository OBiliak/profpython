"""Console application of laboratory work 1: demo and interactive menu."""

import sys

from car_catalog.config import CURRENCY
from car_catalog.models import Car
from car_catalog.services import (
    add_car,
    calculate_average_price,
    filter_cars_by_year,
    find_cars_by_brand,
    find_lowest_mileage_car,
    find_most_expensive_car,
    search_cars,
    sort_cars_by_price,
)


def create_demo_cars() -> list[Car]:
    """Return a demo list of cars."""
    return [
        Car("Toyota", "Corolla", 2018, 520000.0, 85000),
        Car("Toyota", "RAV4", 2021, 1150000.0, 32000),
        Car("Volkswagen", "Golf", 2015, 380000.0, 142000),
        Car("Skoda", "Octavia", 2019, 610000.0, 67000),
        Car("BMW", "X5", 2020, 1890000.0, 54000),
        Car("Renault", "Logan", 2012, 210000.0, 198000),
    ]


def format_car(car: Car) -> str:
    """Return one line with all fields of a car."""
    return (
        f"{car.brand:<11} {car.model:<8} {car.year}  "
        f"{car.price:>11.2f} {CURRENCY}  {car.mileage:>7} км"
    )


def print_cars(cars: list[Car]) -> None:
    """Print cars as a table."""
    if not cars:
        print("Автомобілів не знайдено.")
        return
    for car in cars:
        print(format_car(car))


def print_car(title: str, car: Car | None) -> None:
    """Print a title and one car or a message for an empty result."""
    print(title)
    print(format_car(car) if car else "Автомобілів не знайдено.")


def run_demo() -> None:
    """Run a demonstration scenario with the demo cars."""
    cars = create_demo_cars()
    print("=== Каталог автомобілів (варіант 5) ===")
    print("\nУсі автомобілі:")
    print_cars(cars)

    print("\nПошук за маркою «toyota»:")
    print_cars(find_cars_by_brand(cars, "toyota"))

    print("\nПошук за маркою «Audi»:")
    print_cars(find_cars_by_brand(cars, "Audi"))

    print("\nАвтомобілі 2019 року і новіші:")
    print_cars(filter_cars_by_year(cars, 2019))

    print("\nАвтомобілі 2015–2019 років:")
    print_cars(filter_cars_by_year(cars, 2015, 2019))

    print()
    print_car("Найдорожчий автомобіль:", find_most_expensive_car(cars))

    print(f"\nСередня ціна: {calculate_average_price(cars):.2f} {CURRENCY}")

    print()
    print_car("Автомобіль із найменшим пробігом:", find_lowest_mileage_car(cars))

    print("\nПошук за критеріями: від 2016 року, ціна до 700000 грн:")
    print_cars(search_cars(cars, min_year=2016, max_price=700000))

    print("\nСортування за ціною (від дешевших):")
    print_cars(sort_cars_by_price(cars))

    print("\nПорожній каталог:")
    print_car("Найдорожчий автомобіль:", find_most_expensive_car([]))
    try:
        calculate_average_price([])
    except ValueError as error:
        print(f"Помилка: {error}")


def read_int(prompt: str) -> int:
    """Read an integer from the keyboard until the input is valid."""
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("Введіть ціле число.")


def read_float(prompt: str) -> float:
    """Read a number from the keyboard until the input is valid."""
    while True:
        try:
            return float(input(prompt).replace(",", "."))
        except ValueError:
            print("Введіть число.")


def read_optional_int(prompt: str) -> int | None:
    """Read an integer or return None if the input is empty."""
    text = input(prompt).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        print("Некоректне число, критерій не враховано.")
        return None


def read_optional_float(prompt: str) -> float | None:
    """Read a number or return None if the input is empty."""
    text = input(prompt).strip()
    if not text:
        return None
    try:
        return float(text.replace(",", "."))
    except ValueError:
        print("Некоректне число, критерій не враховано.")
        return None


def print_menu() -> None:
    """Print the menu of the interactive mode."""
    print()
    print("1. Показати всі автомобілі")
    print("2. Додати автомобіль")
    print("3. Пошук за маркою")
    print("4. Фільтр за роком")
    print("5. Найдорожчий автомобіль")
    print("6. Середня ціна")
    print("7. Автомобіль із найменшим пробігом")
    print("8. Пошук за кількома критеріями")
    print("9. Сортування за ціною")
    print("0. Вихід")


def run_menu(cars: list[Car]) -> None:
    """Run the menu-driven interface until the user exits."""
    while True:
        print_menu()
        command = input("Оберіть команду: ").strip()
        try:
            if command == "1":
                print_cars(cars)
            elif command == "2":
                car = Car(
                    input("Марка: ").strip(),
                    input("Модель: ").strip(),
                    read_int("Рік: "),
                    read_float("Ціна: "),
                    read_int("Пробіг, км: "),
                )
                add_car(cars, car)
                print("Автомобіль додано.")
            elif command == "3":
                print_cars(find_cars_by_brand(cars, input("Марка: ")))
            elif command == "4":
                min_year = read_int("Рік від: ")
                max_year = read_optional_int("Рік до (Enter — без обмеження): ")
                print_cars(filter_cars_by_year(cars, min_year, max_year))
            elif command == "5":
                print_car("Найдорожчий автомобіль:", find_most_expensive_car(cars))
            elif command == "6":
                print(f"Середня ціна: {calculate_average_price(cars):.2f} {CURRENCY}")
            elif command == "7":
                print_car("Найменший пробіг:", find_lowest_mileage_car(cars))
            elif command == "8":
                brand = input("Марка (Enter — будь-яка): ")
                min_year = read_optional_int("Рік від (Enter — будь-який): ")
                max_price = read_optional_float("Ціна до (Enter — без обмеження): ")
                print_cars(search_cars(cars, brand, min_year, max_price))
            elif command == "9":
                print_cars(sort_cars_by_price(cars))
            elif command == "0":
                print("До побачення.")
                break
            else:
                print("Невідома команда.")
        except ValueError as error:
            print(f"Помилка: {error}")


def main() -> None:
    """Start the demo or the interactive menu with the --interactive flag."""
    if "--interactive" in sys.argv:
        run_menu(create_demo_cars())
    else:
        run_demo()


if __name__ == "__main__":
    main()
