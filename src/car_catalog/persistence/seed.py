"""Demo data of laboratory work 7: manufacturers and the cars of laboratory works 1–2."""

from sqlalchemy.orm import Session

from car_catalog.data import cars as demo_cars
from car_catalog.persistence.models import Car
from car_catalog.persistence.repositories import CarRepository, ManufacturerRepository

MANUFACTURERS = {
    "Toyota": "Японія",
    "Volkswagen": "Німеччина",
    "Skoda": "Чехія",
    "BMW": "Німеччина",
    "Renault": "Франція",
}

VINS = {
    1: "JTDBR32E720000001",
    2: "JTMRFREV10D000002",
    3: "WVWZZZ1KZFW000003",
    4: "TMBJG7NE0K0000004",
    5: "WBACR610X0L000005",
    6: "VF1LSRAB0C0000006",
    7: "TMBEG6NJ0G0000007",
    8: "JTNB11HK30J000008",
    9: "WVWZZZ3CZHE000009",
    10: "WBA8E1105GK000010",
}


def seed_catalog(session: Session) -> int:
    """Fill an empty database with 5 manufacturers and 10 cars; return the number of cars."""
    manufacturer_repository = ManufacturerRepository(session)
    car_repository = CarRepository(session)
    manufacturer_ids = {
        name: manufacturer_repository.add(name, country).id for name, country in MANUFACTURERS.items()
    }
    for item in demo_cars:
        car_repository.add(
            Car(
                model=item["model"],
                year=item["year"],
                price=item["price"],
                mileage=item["mileage"],
                vin=VINS[item["id"]],
                manufacturer_id=manufacturer_ids[item["brand"]],
            )
        )
    return len(demo_cars)
