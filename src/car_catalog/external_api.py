"""Asynchronous HTTP client of the car catalog API (httpx.AsyncClient, laboratory work 8)."""

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8000"

logger = logging.getLogger("car_catalog.external_api")


@dataclass(frozen=True)
class ClientSettings:
    """Settings of the HTTP client; every value can be changed by an environment variable."""

    base_url: str = DEFAULT_BASE_URL
    timeout: float = 5.0
    retry_attempts: int = 3
    backoff_delay: float = 0.2
    max_concurrency: int = 3

    @classmethod
    def from_env(cls) -> "ClientSettings":
        """Read CAR_CATALOG_API_URL, CAR_CATALOG_HTTP_TIMEOUT, CAR_CATALOG_RETRY_ATTEMPTS, CAR_CATALOG_MAX_CONCURRENCY."""
        return cls(
            base_url=os.environ.get("CAR_CATALOG_API_URL", DEFAULT_BASE_URL),
            timeout=float(os.environ.get("CAR_CATALOG_HTTP_TIMEOUT", "5.0")),
            retry_attempts=int(os.environ.get("CAR_CATALOG_RETRY_ATTEMPTS", "3")),
            max_concurrency=int(os.environ.get("CAR_CATALOG_MAX_CONCURRENCY", "3")),
        )


def create_client(settings: ClientSettings) -> httpx.AsyncClient:
    """One AsyncClient for many requests: it keeps connections open (connection pool)."""
    return httpx.AsyncClient(base_url=settings.base_url, timeout=settings.timeout)


async def fetch_car(client: httpx.AsyncClient, car_id: int) -> dict[str, Any]:
    """GET /cars/{car_id}; an HTTP error status raises httpx.HTTPStatusError."""
    response = await client.get(f"/cars/{car_id}")
    response.raise_for_status()
    data: dict[str, Any] = response.json()
    return data


class ConcurrencyMeter:
    """Counts requests that are running at the same moment (shows that Semaphore works)."""

    def __init__(self) -> None:
        self.current = 0
        self.maximum = 0

    def enter(self) -> None:
        """A request has started."""
        self.current += 1
        self.maximum = max(self.maximum, self.current)

    def leave(self) -> None:
        """A request has finished."""
        self.current -= 1


@dataclass
class GroupResult:
    """Loaded cars and errors of one group request."""

    cars: list[dict[str, Any]]
    errors: list[tuple[int, str]]
    max_concurrency: int


def is_retryable(error: httpx.HTTPError) -> bool:
    """Retry network errors and timeouts (RequestError) and 5xx answers; 4xx will not change."""
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code >= 500
    return isinstance(error, httpx.RequestError)


def describe_error(error: BaseException) -> str:
    """Short text of an error for the result."""
    if isinstance(error, httpx.HTTPStatusError):
        return f"HTTP {error.response.status_code}"
    return f"{type(error).__name__}: {error}" if str(error) else type(error).__name__


async def fetch_with_retry(
    client: httpx.AsyncClient,
    car_id: int,
    attempts: int = 3,
    backoff_delay: float = 0.2,
) -> dict[str, Any]:
    """fetch_car() with retry and exponential backoff: pauses 0.2 s, 0.4 s, 0.8 s, ..."""
    for attempt in range(1, attempts + 1):
        try:
            return await fetch_car(client, car_id)
        except httpx.HTTPError as error:
            if not is_retryable(error) or attempt == attempts:
                raise
            delay = backoff_delay * 2 ** (attempt - 1)
            logger.warning(
                "ID %s: спроба %s з %s невдала (%s), повтор через %.1f с",
                car_id,
                attempt,
                attempts,
                describe_error(error),
                delay,
            )
            await asyncio.sleep(delay)
    raise RuntimeError("attempts має бути не менше 1")


async def fetch_cars(
    client: httpx.AsyncClient,
    car_ids: list[int],
    settings: ClientSettings,
) -> GroupResult:
    """Load a group of cars concurrently: one Task per car, gather, at most max_concurrency at once."""
    semaphore = asyncio.Semaphore(settings.max_concurrency)
    meter = ConcurrencyMeter()

    async def limited_fetch(car_id: int) -> dict[str, Any]:
        async with semaphore:
            meter.enter()
            try:
                return await fetch_with_retry(
                    client, car_id, settings.retry_attempts, settings.backoff_delay
                )
            finally:
                meter.leave()

    tasks = [asyncio.create_task(limited_fetch(car_id), name=f"car-{car_id}") for car_id in car_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    cars: list[dict[str, Any]] = []
    errors: list[tuple[int, str]] = []
    for car_id, result in zip(car_ids, results):
        if isinstance(result, BaseException):
            errors.append((car_id, describe_error(result)))
        else:
            cars.append(result)
    return GroupResult(cars, errors, meter.maximum)


async def load_car_group(
    car_ids: list[int],
    settings: ClientSettings,
    total_timeout: float = 10.0,
) -> GroupResult:
    """Open an AsyncClient and load the group; the whole operation is limited by asyncio.wait_for."""
    async with create_client(settings) as client:
        return await asyncio.wait_for(fetch_cars(client, car_ids, settings), timeout=total_timeout)
