"""Logging configuration: console output and a rotating log file."""

import logging
import sys
from logging.handlers import RotatingFileHandler

from car_catalog.importer.models import LoggingConfig

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
CONSOLE_FORMAT = "%(levelname)s | %(message)s"


def configure_logging(config: LoggingConfig) -> None:
    """Send log records to the console and to a rotating file."""
    config.path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        config.path,
        maxBytes=config.max_bytes,
        backupCount=config.backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(CONSOLE_FORMAT))
    logging.basicConfig(
        level=config.level, handlers=[file_handler, console_handler], force=True
    )


def configure_console_logging() -> None:
    """Log to the console only (used before the configuration is loaded)."""
    logging.basicConfig(
        level=logging.INFO, format=CONSOLE_FORMAT, stream=sys.stdout, force=True
    )
