"""Unit tests of the YAML configuration: year/price ranges and environment overrides."""

from pathlib import Path

import pytest

from car_catalog.importer.config import load_config, to_bool
from car_catalog.importer.exceptions import ConfigurationError


def replace_in_file(path: Path, old: str, new: str) -> None:
    """Replace a fragment of a text file."""
    path.write_text(path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")


def test_loads_year_and_price_ranges(config_file: Path) -> None:
    config = load_config(config_file, environ={})

    assert (config.validation.min_year, config.validation.max_year) == (1950, 2026)
    assert config.filter.max_price == pytest.approx(2_000_000)
    assert config.input.path == config_file.parent / "input.csv"


def test_environment_variable_switches_strict_mode(
    config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CAR_IMPORT_SKIP_INVALID", "false")

    config = load_config(config_file)

    assert config.processing.skip_invalid is False


def test_without_environment_variable_yaml_value_is_used(
    config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CAR_IMPORT_SKIP_INVALID", raising=False)

    config = load_config(config_file)

    assert config.processing.skip_invalid is True


def test_rejects_min_year_greater_than_max(config_file: Path) -> None:
    replace_in_file(config_file, "{min: 1950, max: 2026}", "{min: 2027, max: 2026}")

    with pytest.raises(ConfigurationError, match="min не може бути більшим за max"):
        load_config(config_file, environ={})


@pytest.mark.parametrize(
    "price_range",
    ["{min: -1, max: 2000000}", "{min: 500000, max: 100000}"],
    ids=["negative-min", "min-greater-than-max"],
)
def test_rejects_invalid_price_range(config_file: Path, price_range: str) -> None:
    replace_in_file(config_file, "{min: 0, max: 2000000}", price_range)

    with pytest.raises(ConfigurationError, match="filter.price"):
        load_config(config_file, environ={})


def test_missing_key_error_is_chained(config_file: Path) -> None:
    replace_in_file(config_file, "validation:\n  years: {min: 1950, max: 2026}\n", "")

    with pytest.raises(ConfigurationError, match="немає ключа") as exc_info:
        load_config(config_file, environ={})

    assert isinstance(exc_info.value.__cause__, KeyError)


def test_invalid_bool_in_environment_gives_configuration_error(
    config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CAR_IMPORT_SKIP_INVALID", "maybe")

    with pytest.raises(ConfigurationError, match="Некоректна структура"):
        load_config(config_file)


def test_missing_config_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="не знайдено"):
        load_config(tmp_path / "absent.yaml", environ={})


def test_broken_yaml(tmp_path: Path) -> None:
    path = tmp_path / "broken.yaml"
    path.write_text("input: [unclosed\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="Некоректний YAML"):
        load_config(path, environ={})


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("schema_version: 1", "schema_version: 2", "Непідтримувана версія схеми 2"),
        ("level: INFO", "level: LOUD", "Невідомий рівень logging: LOUD"),
        ("progress_every: 100", "progress_every: 0", "progress_every має бути більшим за 0"),
        ("path: input.csv", "path: absent.csv", "Вхідний файл не знайдено"),
    ],
    ids=["schema-version", "log-level", "progress-step", "missing-input"],
)
def test_rejects_invalid_values(config_file: Path, old: str, new: str, message: str) -> None:
    replace_in_file(config_file, old, new)

    with pytest.raises(ConfigurationError, match=message):
        load_config(config_file, environ={})


def test_rejects_yaml_that_is_not_dictionary(tmp_path: Path) -> None:
    path = tmp_path / "list.yaml"
    path.write_text("- 1\n- 2\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="має бути словником"):
        load_config(path, environ={})


@pytest.mark.parametrize(
    ("value", "expected"),
    [(True, True), ("yes", True), ("1", True), ("False", False), ("no", False), ("0", False)],
)
def test_to_bool_accepts_yaml_and_environment_values(value: object, expected: bool) -> None:
    assert to_bool(value) is expected
