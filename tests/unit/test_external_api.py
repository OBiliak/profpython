"""Unit tests of the async HTTP client: the external HTTP service is replaced by httpx.MockTransport."""

import asyncio
from collections.abc import Awaitable, Callable

import httpx
import pytest

from car_catalog import external_api
from car_catalog.external_api import (
    ClientSettings,
    describe_error,
    fetch_car,
    fetch_cars,
    fetch_with_retry,
    is_retryable,
    load_car_group,
)

Handler = Callable[[httpx.Request], Awaitable[httpx.Response]]


def car_json(car_id: int) -> dict[str, object]:
    return {"id": car_id, "brand": "Toyota", "model": f"Model {car_id}"}


def make_client(handler: Handler) -> httpx.AsyncClient:
    """AsyncClient whose requests go to a test function instead of the network."""
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://test")


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Record backoff pauses instead of waiting."""
    delays: list[float] = []

    async def fake_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr(external_api.asyncio, "sleep", fake_sleep)
    return delays


@pytest.mark.asyncio
async def test_fetch_car_returns_json() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/cars/5"
        return httpx.Response(200, json=car_json(5))

    async with make_client(handler) as client:
        assert await fetch_car(client, 5) == car_json(5)


@pytest.mark.asyncio
async def test_retry_with_exponential_backoff(sleeps: list[float]) -> None:
    answers = [httpx.Response(503), httpx.Response(500), httpx.Response(200, json=car_json(1))]
    calls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return answers.pop(0)

    async with make_client(handler) as client:
        result = await fetch_with_retry(client, 1, attempts=3, backoff_delay=0.2)

    assert result == car_json(1)
    assert len(calls) == 3
    assert sleeps == [0.2, 0.4]


@pytest.mark.asyncio
async def test_404_is_not_retried(sleeps: list[float]) -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(404, json={"error": "not_found"})

    async with make_client(handler) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_with_retry(client, 999)

    assert calls == 1
    assert sleeps == []


@pytest.mark.asyncio
async def test_network_error_is_raised_after_last_attempt(sleeps: list[float]) -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectError("connection refused", request=request)

    async with make_client(handler) as client:
        with pytest.raises(httpx.ConnectError):
            await fetch_with_retry(client, 1, attempts=4, backoff_delay=0.1)

    assert calls == 4
    assert sleeps == [0.1, 0.2, 0.4]


@pytest.mark.asyncio
async def test_timeout_is_retried(sleeps: list[float]) -> None:
    answers: list[httpx.Response | None] = [None, httpx.Response(200, json=car_json(2))]

    async def handler(request: httpx.Request) -> httpx.Response:
        answer = answers.pop(0)
        if answer is None:
            raise httpx.ReadTimeout("timed out", request=request)
        return answer

    async with make_client(handler) as client:
        assert await fetch_with_retry(client, 2) == car_json(2)
    assert sleeps == [0.2]


@pytest.mark.asyncio
async def test_retry_needs_at_least_one_attempt() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    async with make_client(handler) as client:
        with pytest.raises(RuntimeError, match="attempts"):
            await fetch_with_retry(client, 1, attempts=0)


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [1, 2, 3])
async def test_semaphore_limits_concurrent_requests(limit: int) -> None:
    running = 0
    peak = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(0.01)
        running -= 1
        car_id = int(request.url.path.rsplit("/", 1)[1])
        return httpx.Response(200, json=car_json(car_id))

    async with make_client(handler) as client:
        result = await fetch_cars(client, list(range(1, 9)), ClientSettings(max_concurrency=limit))

    assert peak == limit == result.max_concurrency
    assert [car["id"] for car in result.cars] == list(range(1, 9))


@pytest.mark.asyncio
async def test_gather_keeps_order_and_collects_errors(sleeps: list[float]) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        car_id = int(request.url.path.rsplit("/", 1)[1])
        if car_id == 3:
            return httpx.Response(404)
        await asyncio.sleep(0.001 * (5 - car_id))  # later IDs answer first
        return httpx.Response(200, json=car_json(car_id))

    async with make_client(handler) as client:
        result = await fetch_cars(client, [1, 2, 3, 4], ClientSettings())

    assert [car["id"] for car in result.cars] == [1, 2, 4]
    assert result.errors == [(3, "HTTP 404")]


@pytest.mark.asyncio
async def test_load_car_group_total_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    async def slow_handler(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(1)
        return httpx.Response(200, json=car_json(1))

    monkeypatch.setattr(external_api, "create_client", lambda settings: make_client(slow_handler))

    with pytest.raises(TimeoutError):
        await load_car_group([1, 2], ClientSettings(), total_timeout=0.05)


@pytest.mark.asyncio
async def test_load_car_group_opens_and_closes_client(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=car_json(1))

    client = make_client(handler)
    monkeypatch.setattr(external_api, "create_client", lambda settings: client)

    result = await load_car_group([1], ClientSettings())

    assert len(result.cars) == 1
    assert client.is_closed


def test_settings_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CAR_CATALOG_API_URL", "http://127.0.0.1:9000")
    monkeypatch.setenv("CAR_CATALOG_HTTP_TIMEOUT", "2.5")
    monkeypatch.setenv("CAR_CATALOG_RETRY_ATTEMPTS", "5")
    monkeypatch.setenv("CAR_CATALOG_MAX_CONCURRENCY", "4")

    settings = ClientSettings.from_env()

    assert (settings.base_url, settings.timeout, settings.retry_attempts, settings.max_concurrency) == (
        "http://127.0.0.1:9000", 2.5, 5, 4,
    )


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("CAR_CATALOG_API_URL", "CAR_CATALOG_HTTP_TIMEOUT", "CAR_CATALOG_RETRY_ATTEMPTS",
                 "CAR_CATALOG_MAX_CONCURRENCY"):
        monkeypatch.delenv(name, raising=False)

    assert ClientSettings.from_env() == ClientSettings()


def test_create_client_uses_settings() -> None:
    client = external_api.create_client(ClientSettings(base_url="http://example.test", timeout=1.5))

    assert str(client.base_url) == "http://example.test"
    assert client.timeout.read == 1.5


REQUEST = httpx.Request("GET", "http://test/cars/1")


@pytest.mark.parametrize(
    ("error", "retryable", "text"),
    [
        (httpx.HTTPStatusError("e", request=REQUEST, response=httpx.Response(503)), True, "HTTP 503"),
        (httpx.HTTPStatusError("e", request=REQUEST, response=httpx.Response(404)), False, "HTTP 404"),
        (httpx.ConnectError("refused", request=REQUEST), True, "ConnectError: refused"),
        (httpx.ConnectTimeout("", request=REQUEST), True, "ConnectTimeout"),
    ],
    ids=["503", "404", "connect", "timeout"],
)
def test_retryable_errors(error: httpx.HTTPError, retryable: bool, text: str) -> None:
    assert is_retryable(error) is retryable
    assert describe_error(error) == text
