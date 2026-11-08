"""Tests for the OpenAPI export: docs/openapi.json is the current schema of the API."""

import json
from pathlib import Path

import pytest

from car_catalog.openapi_export import main, openapi_text

DOCS_SCHEMA = Path(__file__).resolve().parents[2] / "docs" / "openapi.json"


def test_docs_schema_is_up_to_date() -> None:
    # if this test fails: python -m car_catalog.openapi_export
    assert DOCS_SCHEMA.read_text(encoding="utf-8") == openapi_text()


def test_export_writes_schema_with_variant_paths(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "api" / "openapi.json"
    assert main([str(path)]) == 0
    schema = json.loads(path.read_text(encoding="utf-8"))
    for route in ("/cars", "/manufacturers", "/manufacturers/{manufacturer_id}/cars", "/health"):
        assert route in schema["paths"]
    assert f"→ {path}" in capsys.readouterr().out
