"""Unit tests of the external vehicle info service with Mock, autospec and AsyncMock."""

from collections.abc import Callable
from unittest.mock import AsyncMock, Mock, call, create_autospec

import pytest

from car_catalog.domain.models import Car
from car_catalog.domain.protocols import EventLogger
from car_catalog.domain.vehicle_info import (
    AsyncVehicleInfoService,
    LocalVehicleInfoProvider,
    VehicleInfo,
    VehicleInfoError,
    VehicleInfoProvider,
    VehicleInfoService,
)

BMW_INFO = VehicleInfo("BMW", "X5", "Німеччина")


@pytest.fixture
def provider() -> Mock:
    """Return a Mock of the external provider limited by its Protocol (spec)."""
    return Mock(spec=VehicleInfoProvider)


@pytest.fixture
def event_logger() -> Mock:
    """Return a Mock logger to check interactions."""
    return Mock(spec=EventLogger)


def test_returns_info_from_provider(
    provider: Mock, event_logger: Mock, make_car: Callable[..., Car]
) -> None:
    provider.fetch.return_value = BMW_INFO
    service = VehicleInfoService(provider, event_logger)

    info = service.get_info(make_car(5, "BMW", "X5"))

    assert info.country == "Німеччина"
    provider.fetch.assert_called_once_with("BMW", "X5")
    event_logger.log.assert_called_once_with("довідка для ID 5: Німеччина")


def test_provider_failure_raises_domain_error_without_logging(
    provider: Mock, event_logger: Mock, make_car: Callable[..., Car]
) -> None:
    provider.fetch.side_effect = ConnectionError("сервіс недоступний")
    service = VehicleInfoService(provider, event_logger)

    with pytest.raises(VehicleInfoError, match="ID 5") as exc_info:
        service.get_info(make_car(5, "BMW", "X5"))

    assert isinstance(exc_info.value.__cause__, ConnectionError)
    event_logger.log.assert_not_called()


def test_collect_info_skips_failed_requests(
    provider: Mock, event_logger: Mock, make_car: Callable[..., Car]
) -> None:
    provider.fetch.side_effect = [BMW_INFO, TimeoutError("timeout")]
    service = VehicleInfoService(provider, event_logger)
    cars = [make_car(5, "BMW", "X5"), make_car(17, "Peugeot", "308")]

    result = service.collect_info(cars)

    assert list(result) == [5]
    assert provider.fetch.call_args_list == [call("BMW", "X5"), call("Peugeot", "308")]
    assert event_logger.log.call_count == 2


def test_autospec_checks_method_signature() -> None:
    provider = create_autospec(LocalVehicleInfoProvider, instance=True)

    with pytest.raises(TypeError):
        provider.fetch("BMW")

    provider.fetch.assert_not_called()


def test_local_provider_knows_brand_country() -> None:
    assert LocalVehicleInfoProvider().fetch("Skoda", "Octavia").country == "Чехія"


def test_local_provider_raises_lookup_error_for_unknown_brand() -> None:
    with pytest.raises(LookupError, match="Peugeot"):
        LocalVehicleInfoProvider().fetch("Peugeot", "308")


@pytest.mark.asyncio
async def test_async_service_returns_country(make_car: Callable[..., Car]) -> None:
    client = AsyncMock()
    client.fetch_info.return_value = {"brand": "Tesla", "model": "Model 3", "country": "США"}
    service = AsyncVehicleInfoService(client)

    country = await service.get_country(make_car(6, "Tesla", "Model 3"))

    assert country == "США"
    client.fetch_info.assert_awaited_once_with("Tesla", "Model 3")


@pytest.mark.asyncio
async def test_async_service_wraps_timeout(make_car: Callable[..., Car]) -> None:
    client = AsyncMock()
    client.fetch_info.side_effect = TimeoutError("немає відповіді")
    service = AsyncVehicleInfoService(client)

    with pytest.raises(VehicleInfoError) as exc_info:
        await service.get_country(make_car(6, "Tesla", "Model 3"))

    assert isinstance(exc_info.value.__cause__, TimeoutError)
    client.fetch_info.assert_awaited_once()
