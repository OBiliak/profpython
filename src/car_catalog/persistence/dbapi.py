"""Python DB-API (sqlite3) without ORM: parameterized search of cars by brand/manufacturer."""

import sqlite3

CarRow = tuple[int, str, str, int, float, int]


def find_cars_by_manufacturer(database_path: str, manufacturer: str) -> list[CarRow]:
    """Return (id, brand, model, year, price, mileage) of cars of one manufacturer.

    The brand is passed as a parameter (?), so the driver never inserts it into the SQL text
    and SQL injection is not possible.
    """
    connection = sqlite3.connect(database_path)
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT cars.id, manufacturers.name, cars.model, cars.year, cars.price, cars.mileage
            FROM cars
            JOIN manufacturers ON cars.manufacturer_id = manufacturers.id
            WHERE lower(manufacturers.name) = lower(?)
            ORDER BY cars.id
            """,
            (manufacturer.strip(),),
        )
        rows: list[CarRow] = cursor.fetchall()
    finally:
        connection.close()
    return rows


def count_cars_by_country(database_path: str) -> list[tuple[str, int]]:
    """COUNT of cars per manufacturer country (JOIN + GROUP BY via DB-API)."""
    connection = sqlite3.connect(database_path)
    try:
        cursor = connection.execute(
            """
            SELECT manufacturers.country, COUNT(cars.id) AS car_count
            FROM manufacturers
            JOIN cars ON cars.manufacturer_id = manufacturers.id
            GROUP BY manufacturers.country
            ORDER BY car_count DESC, manufacturers.country
            """
        )
        rows: list[tuple[str, int]] = cursor.fetchall()
    finally:
        connection.close()
    return rows
