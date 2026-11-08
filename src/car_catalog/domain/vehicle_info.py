"""External vehicle info service: provider Protocols, a local provider and services."""

from dataclasses import dataclass
from typing import Protocol

from car_catalog.domain.exceptions import CatalogError
from car_catalog.domain.models import Vehicle
from car_catalog.domain.protocols import EventLogger

BRAND_COUNTRIES = {
    "Audi": "Німеччина",
    "BMW": "Німеччина",
    "Mercedes-Benz": "Німеччина",
    "Volkswagen": "Німеччина",
    "Porsche": "Німеччина",
    "Opel": "Німеччина",
    "Toyota": "Японія",
    "Nissan": "Японія",
    "Mitsubishi": "Японія",
    "Skoda": "Чехія",
    "Tesla": "США",
    "Hyundai": "Південна Корея",
}


@dataclass(frozen=True, slots=True)
class VehicleInfo:
    """Reference data about a vehicle model from an external service."""

    brand: str
    model: str
    country: str


class VehicleInfoError(CatalogError):
    """Raised when the external vehicle info service cannot give an answer."""


class VehicleInfoProvider(Protocol):
    """External service that returns reference data by brand and model."""

    def fetch(self, brand: str, model: str) -> VehicleInfo:
        """Return reference data or raise an error of the service."""
        ...


class AsyncVehicleInfoClient(Protocol):
    """Asynchronous client of the external vehicle info service."""

    async def fetch_info(self, brand: str, model: str) -> dict[str, str]:
        """Return the JSON answer of the service as a dictionary."""
        ...


class LocalVehicleInfoProvider:
    """Offline provider with reference data (stands in for a remote service)."""

    def fetch(self, brand: str, model: str) -> VehicleInfo:
        """Return the country of the brand or raise LookupError."""
        country = BRAND_COUNTRIES.get(brand)
        if country is None:
            raise LookupError(f"Немає довідки про марку {brand}")
        return VehicleInfo(brand, model, country)


class LocalAsyncVehicleInfoClient:
    """Asynchronous version of the local provider for the demo scenario."""

    async def fetch_info(self, brand: str, model: str) -> dict[str, str]:
        """Return the answer in the format of the remote service."""
        info = LocalVehicleInfoProvider().fetch(brand, model)
        return {"brand": info.brand, "model": info.model, "country": info.country}


class VehicleInfoService:
    """Gets reference data for vehicles; the provider and logger are injected."""

    def __init__(self, provider: VehicleInfoProvider, logger: EventLogger) -> None:
        self._provider = provider
        self._logger = logger

    def get_info(self, vehicle: Vehicle) -> VehicleInfo:
        """Return reference data of a vehicle or raise VehicleInfoError."""
        try:
            info = self._provider.fetch(vehicle.brand, vehicle.model)
        except (LookupError, ConnectionError, TimeoutError) as error:
            raise VehicleInfoError(f"Не вдалося отримати довідку для ID {vehicle.id}") from error
        self._logger.log(f"довідка для ID {vehicle.id}: {info.country}")
        return info

    def collect_info(self, vehicles: list[Vehicle]) -> dict[int, VehicleInfo]:
        """Return reference data by vehicle ID; failed requests are skipped."""
        result: dict[int, VehicleInfo] = {}
        for vehicle in vehicles:
            try:
                result[vehicle.id] = self.get_info(vehicle)
            except VehicleInfoError as error:
                self._logger.log(f"пропущено: {error}")
        return result


class AsyncVehicleInfoService:
    """Asynchronous service that asks the external client about the country of a vehicle."""

    def __init__(self, client: AsyncVehicleInfoClient) -> None:
        self._client = client

    async def get_country(self, vehicle: Vehicle) -> str:
        """Return the country of the vehicle brand from the external service."""
        try:
            data = await self._client.fetch_info(vehicle.brand, vehicle.model)
        except (LookupError, ConnectionError, TimeoutError) as error:
            raise VehicleInfoError(f"Не вдалося отримати довідку для ID {vehicle.id}") from error
        return data["country"]
