"""Entry point: REST API of the car catalog on a real Uvicorn server (laboratory work 8, variant 5).

python -m car_catalog.main starts the API at http://127.0.0.1:8000, sends HTTP requests to it with
httpx.AsyncClient and stops the server. To work with Swagger UI: uvicorn car_catalog.api:app
"""

import asyncio
import json
import logging
import sys
import threading
import time
from pathlib import Path
from typing import Any

import httpx
import uvicorn

from car_catalog.api import app
from car_catalog.external_api import ClientSettings, create_client, load_car_group
from car_catalog.importer.logging_config import configure_console_logging
from car_catalog.persistence.database import DATABASE_PATH, SessionLocal
from car_catalog.persistence.migrations import upgrade_database
from car_catalog.persistence.seed import seed_catalog

HOST = "127.0.0.1"
DEFAULT_PORT = 8000
GROUP = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


class ServerThread:
    """Uvicorn server in a background thread of this process."""

    def __init__(self, port: int) -> None:
        config = uvicorn.Config(app, host=HOST, port=port, log_level="warning")
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def start(self) -> None:
        """Start the server and wait until it accepts connections."""
        self.thread.start()
        while not self.server.started:
            if not self.thread.is_alive():
                raise RuntimeError("Сервер не запустився (порт зайнятий?)")
            time.sleep(0.05)

    def stop(self) -> None:
        """Ask the server to finish and wait for the thread."""
        self.server.should_exit = True
        self.thread.join()


def prepare_database() -> None:
    """Recreate car_catalog.db with Alembic migrations and fill it with the demo cars."""
    Path(DATABASE_PATH).unlink(missing_ok=True)
    upgrade_database(f"sqlite:///{DATABASE_PATH}")
    with SessionLocal() as session:
        seed_catalog(session)


def show(response: httpx.Response) -> Any:
    """Print the request line, the status code and the JSON body; return the JSON."""
    request = response.request
    target = request.url.raw_path.decode()
    data = response.json() if response.content else None
    body = f"\n    {json.dumps(data, ensure_ascii=False)}" if data is not None else ""
    print(f"{request.method} {httpx.URL(target)} → {response.status_code} {response.reason_phrase}{body}")
    return data


async def show_endpoints(client: httpx.AsyncClient) -> None:
    """Call every endpoint: GET, POST, PATCH, DELETE, path and query parameters, errors."""
    print("\n--- GET: читання, path і query parameters ---")
    show(await client.get("/"))
    show(await client.get("/cars", params={"brand": "Toyota"}))
    show(await client.get("/cars", params={"model": "o", "min_year": 2016, "max_year": 2019}))
    show(await client.get("/cars", params={"sort_by": "price", "descending": "true", "limit": 3, "offset": 0}))
    show(await client.get("/cars/5"))
    show(await client.get("/cars/statistics"))
    show(await client.get("/manufacturers"))
    show(await client.get("/manufacturers/3/cars"))

    print("\n--- POST, PATCH, DELETE ---")
    new_car = {"manufacturer_id": 1, "model": "Prius", "year": 2020, "price": 720000,
               "mileage": 45000, "vin": "JTDKN3DU0A0000011"}
    print(f"JSON request: {json.dumps(new_car, ensure_ascii=False)}")
    created = show(await client.post("/cars", json=new_car))
    show(await client.patch(f"/cars/{created['id']}", json={"price": 705000, "mileage": 47500}))
    show(await client.delete(f"/cars/{created['id']}"))
    show(await client.get(f"/cars/{created['id']}"))

    print("\n--- Помилки: validation (422), not found (404), conflict (409) ---")
    show(await client.post("/cars", json={**new_car, "year": 1949, "price": 0, "vin": "123"}))
    show(await client.patch("/cars/1", json={}))
    show(await client.get("/cars", params={"min_year": 2022, "max_year": 2019}))
    show(await client.get("/cars/999"))
    show(await client.get("/manufacturers/99/cars"))
    show(await client.post("/cars", json={**new_car, "vin": "JTDBR32E720000001"}))


async def show_concurrency(base_url: str) -> None:
    """Group loading with Task + gather and Semaphore(1) / Semaphore(3), batch endpoint, retry, timeout."""
    print("\n--- Асинхронне завантаження групи автомобілів (HTTPX, Task, gather, Semaphore) ---")
    for limit in (1, 3):
        settings = ClientSettings(base_url=base_url, max_concurrency=limit)
        result = await load_car_group(GROUP, settings)
        print(f"Semaphore({limit}): {len(GROUP)} tasks, завантажено {len(result.cars)}, помилок {len(result.errors)}, "
              f"одночасно виконувалось не більше {result.max_concurrency}")
    print("Моделі: " + ", ".join(f"{car['brand']} {car['model']}" for car in result.cars))

    async with create_client(settings) as client:
        show(await client.post("/cars/batch", json={"car_ids": [1, 2, 5, 8, 999]}))

    print("\n--- Retry з exponential backoff: порт 8001, на якому немає сервера ---")
    offline = ClientSettings(base_url=f"http://{HOST}:8001", retry_attempts=3, backoff_delay=0.2)
    started = time.perf_counter()
    result = await load_car_group([1, 2], offline)
    print(f"Результат після 3 спроб: {result.errors} ({time.perf_counter() - started:.1f} с)")

    print("\n--- Timeout ---")
    tiny = ClientSettings(base_url=base_url, timeout=0.000001, retry_attempts=1)
    result = await load_car_group([1, 2, 3], tiny)
    print(f"httpx timeout 0.000001 с: {result.errors}")
    try:
        await load_car_group([1, 2], offline, total_timeout=0.3)
    except TimeoutError:
        print("asyncio.wait_for(timeout=0.3): операцію скасовано — TimeoutError")


def main(argv: list[str] | None = None) -> int:
    """Run the REST API scenario of laboratory work 8; return the exit code."""
    args = sys.argv[1:] if argv is None else argv
    port = int(args[0]) if args else DEFAULT_PORT
    configure_console_logging()
    logging.getLogger("httpx").setLevel(logging.WARNING)
    print("=== Каталог автомобілів: REST API (лабораторна робота №8, варіант 5) ===")
    prepare_database()
    base_url = f"http://{HOST}:{port}"
    server = ServerThread(port)
    try:
        server.start()
    except RuntimeError as error:
        print(f"Помилка: {error}")
        return 1
    print(f"БД {DATABASE_PATH} створено міграціями; Uvicorn: {base_url} (Swagger UI: {base_url}/docs)")
    try:
        asyncio.run(run_client(base_url))
    finally:
        server.stop()
    print("\nСервер зупинено. Swagger UI: uvicorn car_catalog.api:app → http://127.0.0.1:8000/docs")
    return 0


async def run_client(base_url: str) -> None:
    """All client requests of the demo."""
    async with httpx.AsyncClient(base_url=base_url, timeout=5.0) as client:
        await show_endpoints(client)
    await show_concurrency(base_url)


if __name__ == "__main__":
    raise SystemExit(main())
