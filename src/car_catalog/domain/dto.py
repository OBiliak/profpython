"""External payload (TypedDict) and its conversion to domain objects."""

from typing import NotRequired, TypedDict

from car_catalog.domain.exceptions import InvalidVehicleError
from car_catalog.domain.models import Car, ElectricCar, Vehicle
from car_catalog.domain.value_objects import Mileage, Money


class VehiclePayload(TypedDict):
    """Vehicle data as it comes from outside, for example from JSON."""

    id: int
    kind: str
    brand: str
    model: str
    year: int
    price: float
    mileage: int
    battery_kwh: NotRequired[float]
    range_km: NotRequired[int]


def vehicle_from_payload(data: VehiclePayload) -> Vehicle:
    """Factory: create Car or ElectricCar depending on the kind field."""
    price = Money(data["price"])
    mileage = Mileage(data["mileage"])
    if data["kind"] == "car":
        return Car(data["id"], data["brand"], data["model"], data["year"], price, mileage)
    if data["kind"] == "electric":
        if "battery_kwh" not in data or "range_km" not in data:
            raise InvalidVehicleError("Для електромобіля потрібні battery_kwh і range_km.")
        return ElectricCar(
            data["id"],
            data["brand"],
            data["model"],
            data["year"],
            price,
            mileage,
            data["battery_kwh"],
            data["range_km"],
        )
    raise InvalidVehicleError(f"Невідомий тип транспорту: {data['kind']}.")


def vehicle_to_payload(vehicle: Vehicle) -> VehiclePayload:
    """Convert a domain object back to an external payload."""
    payload: VehiclePayload = {
        "id": vehicle.id,
        "kind": "car",
        "brand": vehicle.brand,
        "model": vehicle.model,
        "year": vehicle.year,
        "price": vehicle.price.amount,
        "mileage": vehicle.mileage.km,
    }
    if isinstance(vehicle, ElectricCar):
        payload["kind"] = "electric"
        payload["battery_kwh"] = vehicle.battery_kwh
        payload["range_km"] = vehicle.range_km
    return payload
