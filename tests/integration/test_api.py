"""API integration tests: FastAPI + Pydantic + repositories + the test SQLite database."""

import asyncio
import logging

import httpx
import pytest
from fastapi.testclient import TestClient

from car_catalog import api
from car_catalog.api import app, get_http_client

pytestmark = pytest.mark.integration

NEW_CAR = {
    "manufacturer_id": 1,
    "model": "Prius",
    "year": 2020,
    "price": 720000,
    "mileage": 45000,
    "vin": "JTDKN3DU0A0000011",
}


def ids(response: httpx.Response) -> list[int]:
    """IDs of the cars in a JSON list."""
    return [car["id"] for car in response.json()]


def test_root(api_client: TestClient) -> None:
    response = api_client.get("/")

    assert response.status_code == 200
    assert response.json()["name"] == "Car Catalog API"


# --- GET /cars: query parameters ---


def test_list_cars_returns_all_cars(api_client: TestClient) -> None:
    response = api_client.get("/cars")

    assert response.status_code == 200
    assert ids(response) == list(range(1, 11))
    assert response.json()[0] == {
        "id": 1,
        "brand": "Toyota",
        "model": "Corolla",
        "year": 2018,
        "price": 520000.0,
        "mileage": 85000,
        "vin": "JTDBR32E720000001",
        "manufacturer_id": 1,
    }


@pytest.mark.parametrize(
    ("params", "expected_ids"),
    [
        ({"brand": "toyota"}, [1, 2, 8]),
        ({"model": "o"}, [1, 3, 4, 6]),
        ({"min_year": 2016, "max_year": 2019}, [1, 4, 7, 8, 9, 10]),
        ({"brand": "Skoda", "min_year": 2017}, [4]),
        ({"min_year": 2023}, []),
        ({"sort_by": "price", "descending": True, "limit": 3}, [5, 2, 8]),
        ({"sort_by": "mileage", "limit": 2, "offset": 2}, [8, 4]),
    ],
    ids=["brand", "model", "years", "brand-and-year", "empty", "sort-limit", "page"],
)
def test_list_cars_with_query_parameters(
    api_client: TestClient, params: dict[str, object], expected_ids: list[int]
) -> None:
    response = api_client.get("/cars", params=params)

    assert response.status_code == 200
    assert ids(response) == expected_ids


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": 101},
        {"offset": -1},
        {"min_year": 1949},
        {"sort_by": "brand"},
        {"min_year": 2022, "max_year": 2019},
    ],
    ids=["limit-0", "limit-101", "offset", "min-year", "sort-field", "reversed-years"],
)
def test_list_cars_rejects_invalid_query(api_client: TestClient, params: dict[str, object]) -> None:
    response = api_client.get("/cars", params=params)

    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"


# --- GET /cars/{id}, statistics ---


def test_get_car(api_client: TestClient) -> None:
    response = api_client.get("/cars/5")

    assert response.status_code == 200
    assert (response.json()["brand"], response.json()["model"]) == ("BMW", "X5")


def test_get_missing_car_returns_structured_404(api_client: TestClient) -> None:
    response = api_client.get("/cars/999")

    assert response.status_code == 404
    assert response.json() == {"error": "not_found", "detail": "Автомобіль з ID 999 не знайдено"}


def test_get_car_with_text_id_is_422(api_client: TestClient) -> None:
    assert api_client.get("/cars/abc").status_code == 422


def test_statistics(api_client: TestClient) -> None:
    data = api_client.get("/cars/statistics").json()

    assert data["count"] == 10
    assert data["average_price"] == pytest.approx(758000)
    assert data["most_expensive"]["model"] == "X5"
    assert data["lowest_mileage"]["model"] == "RAV4"


def test_statistics_of_empty_catalog(api_client: TestClient) -> None:
    for car_id in range(1, 11):
        assert api_client.delete(f"/cars/{car_id}").status_code == 204

    data = api_client.get("/cars/statistics").json()

    assert data == {
        "count": 0,
        "average_price": 0.0,
        "most_expensive": None,
        "lowest_mileage": None,
    }


# --- POST /cars ---


def test_create_car(api_client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="car_catalog.api"):
        response = api_client.post("/cars", json=NEW_CAR)

    assert response.status_code == 201
    created = response.json()
    assert created["id"] == 11 and created["brand"] == "Toyota"
    assert api_client.get("/cars/11").json() == created
    assert "Додано автомобіль 11: Toyota Prius" in caplog.text  # background task


def test_create_car_of_missing_manufacturer(api_client: TestClient) -> None:
    response = api_client.post("/cars", json={**NEW_CAR, "manufacturer_id": 99})

    assert response.status_code == 404
    assert response.json()["detail"] == "Виробника з ID 99 не знайдено"


def test_create_car_with_duplicate_vin_is_409(api_client: TestClient) -> None:
    response = api_client.post("/cars", json={**NEW_CAR, "vin": "JTDBR32E720000001"})

    assert response.status_code == 409
    assert response.json() == {
        "error": "conflict",
        "detail": "База даних відхилила запис: UNIQUE constraint failed: cars.vin",
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("year", 1949),
        ("year", 2027),
        ("price", 0),
        ("price", -1),
        ("mileage", -1),
        ("model", ""),
        ("vin", "JTDKN3DU0A000001"),
        ("vin", "JTDKN3DU0A00000I1"),
        ("manufacturer_id", 0),
    ],
)
def test_create_car_validation(api_client: TestClient, field: str, value: object) -> None:
    response = api_client.post("/cars", json={**NEW_CAR, field: value})

    assert response.status_code == 422
    assert f"body.{field}" in response.json()["detail"]


def test_create_car_without_required_field(api_client: TestClient) -> None:
    body = {key: value for key, value in NEW_CAR.items() if key != "price"}

    response = api_client.post("/cars", json=body)

    assert response.status_code == 422
    assert response.json()["detail"] == "body.price: Field required"


def test_create_car_boundary_values(api_client: TestClient) -> None:
    response = api_client.post(
        "/cars", json={**NEW_CAR, "year": 1950, "price": 0.01, "mileage": 0, "vin": None}
    )

    assert response.status_code == 201


# --- PATCH /cars/{id} ---


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ({"price": 505000}, (505000.0, 85000)),
        ({"mileage": 90000}, (520000.0, 90000)),
        ({"price": 499000, "mileage": 91000}, (499000.0, 91000)),
    ],
    ids=["price", "mileage", "both"],
)
def test_update_price_and_mileage(
    api_client: TestClient, body: dict[str, object], expected: tuple[float, int]
) -> None:
    response = api_client.patch("/cars/1", json=body)

    assert response.status_code == 200
    data = api_client.get("/cars/1").json()
    assert (
        (data["price"], data["mileage"])
        == expected
        == (response.json()["price"], response.json()["mileage"])
    )


@pytest.mark.parametrize(
    "body", [{}, {"price": -5}, {"mileage": -1}], ids=["empty", "price", "mileage"]
)
def test_update_validation(api_client: TestClient, body: dict[str, object]) -> None:
    assert api_client.patch("/cars/1", json=body).status_code == 422
    assert api_client.get("/cars/1").json()["price"] == 520000.0


def test_update_missing_car(api_client: TestClient) -> None:
    assert api_client.patch("/cars/999", json={"price": 1}).status_code == 404


# --- DELETE /cars/{id} ---


def test_delete_car(api_client: TestClient) -> None:
    response = api_client.delete("/cars/6")

    assert response.status_code == 204
    assert response.content == b""
    assert api_client.get("/cars/6").status_code == 404
    assert api_client.delete("/cars/6").status_code == 404


# --- manufacturers ---


def test_list_manufacturers(api_client: TestClient) -> None:
    names = [item["name"] for item in api_client.get("/manufacturers").json()]

    assert names == ["BMW", "Renault", "Skoda", "Toyota", "Volkswagen"]


def test_manufacturer_cars(api_client: TestClient) -> None:
    response = api_client.get("/manufacturers/3/cars")

    assert response.status_code == 200
    assert [car["model"] for car in response.json()] == ["Octavia", "Fabia"]


def test_manufacturer_cars_of_missing_manufacturer(api_client: TestClient) -> None:
    assert api_client.get("/manufacturers/99/cars").status_code == 404


# --- POST /cars/batch: asynchronous loading through GET /cars/{id} ---


def test_batch_loads_group_and_reports_missing_cars(api_client: TestClient) -> None:
    response = api_client.post("/cars/batch", json={"car_ids": [1, 2, 5, 8, 999]})

    assert response.status_code == 200
    data = response.json()
    assert ids(httpx.Response(200, json=data["cars"])) == [1, 2, 5, 8]
    assert data["errors"] == [{"car_id": 999, "error": "HTTP 404"}]
    assert 1 <= data["max_concurrency"] <= 3


@pytest.mark.parametrize("car_ids", [[], list(range(1, 52))], ids=["empty", "too-many"])
def test_batch_validation(api_client: TestClient, car_ids: list[int]) -> None:
    assert api_client.post("/cars/batch", json={"car_ids": car_ids}).status_code == 422


# --- OpenAPI and async client ---


def test_openapi_describes_variant_endpoints(api_client: TestClient) -> None:
    schema = api_client.get("/openapi.json").json()

    assert schema["info"]["title"] == "Car Catalog API"
    assert {
        "/cars",
        "/cars/{car_id}",
        "/manufacturers/{manufacturer_id}/cars",
        "/cars/batch",
    } <= set(schema["paths"])
    assert set(schema["paths"]["/cars/{car_id}"]) == {"get", "patch", "delete"}


@pytest.mark.asyncio
async def test_api_through_async_client(api_client: TestClient) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/cars/2")

    assert response.status_code == 200
    assert response.json()["model"] == "RAV4"


def test_batch_timeout_returns_504(api_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def slow_handler(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(1)
        return httpx.Response(200, json={})

    slow_client = httpx.AsyncClient(
        transport=httpx.MockTransport(slow_handler), base_url="http://test"
    )
    monkeypatch.setattr(api, "BATCH_TIMEOUT", 0.05)
    app.dependency_overrides[get_http_client] = lambda: slow_client

    response = api_client.post("/cars/batch", json={"car_ids": [1, 2]})

    assert response.status_code == 504
    assert response.json() == {
        "error": "timeout",
        "detail": "Пакетне завантаження не завершилося вчасно",
    }
