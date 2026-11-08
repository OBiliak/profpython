"""Asynchronous HTTP client of the car catalog API (httpx.AsyncClient, laboratory work 8)."""

import os
from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8000"


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
