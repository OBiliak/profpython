"""Loading and validation of the YAML configuration."""

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from car_catalog.importer.exceptions import ConfigurationError
from car_catalog.importer.models import (
    AppConfig,
    FilterConfig,
    InputConfig,
    LoggingConfig,
    OutputConfig,
    ProcessingConfig,
    ValidationConfig,
)

SCHEMA_VERSION = 1
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
ENV_OVERRIDES = {
    "CAR_IMPORT_INPUT": ("input", "path"),
    "CAR_IMPORT_SKIP_INVALID": ("processing", "skip_invalid"),
    "CAR_IMPORT_LOG_LEVEL": ("logging", "level"),
}


def read_yaml(path: Path) -> dict[str, Any]:
    """Read a YAML file into a dictionary."""
    try:
        with path.open(encoding="utf-8") as file:
            raw = yaml.safe_load(file)
    except FileNotFoundError as error:
        raise ConfigurationError(f"Файл конфігурації не знайдено: {path}") from error
    except yaml.YAMLError as error:
        raise ConfigurationError(f"Некоректний YAML у файлі {path}") from error
    if not isinstance(raw, dict):
        raise ConfigurationError("Конфігурація має бути словником YAML.")
    return raw


def apply_env_overrides(raw: dict[str, Any], environ: Mapping[str, str]) -> None:
    """Replace configuration values with environment variables if they are set."""
    for name, (section, key) in ENV_OVERRIDES.items():
        if name in environ:
            raw.setdefault(section, {})[key] = environ[name]


def to_bool(value: object) -> bool:
    """Convert a YAML or environment value to bool."""
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("true", "yes", "1"):
        return True
    if text in ("false", "no", "0"):
        return False
    raise ValueError(f"Очікувалось true або false, отримано {value!r}")


def build_config(raw: dict[str, Any], base: Path) -> AppConfig:
    """Build configuration dataclasses from the nested YAML dictionary."""
    output = raw["output"]
    return AppConfig(
        schema_version=int(raw["schema_version"]),
        input=InputConfig(path=base / raw["input"]["path"]),
        output=OutputConfig(
            path=base / output["path"],
            errors_path=base / output["errors_path"],
            summary_path=base / output["summary_path"],
            backup=to_bool(output.get("backup", False)),
        ),
        validation=ValidationConfig(
            min_year=int(raw["validation"]["years"]["min"]),
            max_year=int(raw["validation"]["years"]["max"]),
        ),
        filter=FilterConfig(
            min_price=float(raw["filter"]["price"]["min"]),
            max_price=float(raw["filter"]["price"]["max"]),
        ),
        processing=ProcessingConfig(
            skip_invalid=to_bool(raw["processing"]["skip_invalid"]),
            progress_every=int(raw["processing"].get("progress_every", 1000)),
        ),
        logging=LoggingConfig(
            level=str(raw["logging"]["level"]).upper(),
            path=base / raw["logging"]["path"],
            max_bytes=int(raw["logging"].get("max_bytes", 1_000_000)),
            backup_count=int(raw["logging"].get("backup_count", 3)),
        ),
    )


def validate_config(config: AppConfig) -> None:
    """Check values of the configuration (fail-fast)."""
    if config.schema_version != SCHEMA_VERSION:
        raise ConfigurationError(
            f"Непідтримувана версія схеми {config.schema_version}, очікується {SCHEMA_VERSION}."
        )
    if config.validation.min_year > config.validation.max_year:
        raise ConfigurationError("validation.years: min не може бути більшим за max.")
    if not 0 <= config.filter.min_price <= config.filter.max_price:
        raise ConfigurationError("filter.price: потрібно 0 <= min <= max.")
    if config.logging.level not in LOG_LEVELS:
        raise ConfigurationError(f"Невідомий рівень logging: {config.logging.level}")
    if config.processing.progress_every <= 0:
        raise ConfigurationError("processing.progress_every має бути більшим за 0.")
    if not config.input.path.is_file():
        raise ConfigurationError(f"Вхідний файл не знайдено: {config.input.path}")


def load_config(path: Path, environ: Mapping[str, str] = os.environ) -> AppConfig:
    """Load, override from the environment and validate the configuration."""
    raw = read_yaml(path)
    apply_env_overrides(raw, environ)
    try:
        config = build_config(raw, path.parent)
    except KeyError as error:
        raise ConfigurationError(f"У конфігурації немає ключа {error}") from error
    except (TypeError, ValueError) as error:
        raise ConfigurationError(f"Некоректна структура конфігурації: {error}") from error
    validate_config(config)
    return config
