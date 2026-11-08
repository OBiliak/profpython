"""Production entry point of the car catalog: python -m car_catalog.main (console script car-catalog).

Reads the settings from environment variables (and .env), configures logging, applies database
migrations, fills an empty database with demo data if SEED_DEMO_DATA=true and starts the REST API
with Uvicorn. Demos of the laboratory works: car_catalog.performance_demo (9), api_demo (8),
database_app (7), catalog_app (6), importer.app (5), console (1).
"""

import logging

import uvicorn

from car_catalog import __version__
from car_catalog.config import Settings, get_settings
from car_catalog.persistence.database import create_database_engine, create_session_factory
from car_catalog.persistence.migrations import upgrade_database
from car_catalog.persistence.repositories import ManufacturerRepository
from car_catalog.persistence.seed import seed_catalog

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"

logger = logging.getLogger("car_catalog")


def configure_logging(level: str) -> None:
    """Log records of the application to stderr with time and level (LOG_LEVEL)."""
    logging.basicConfig(level=level, format=LOG_FORMAT, force=True)


def prepare_database(settings: Settings) -> int:
    """Apply migrations; with seed_demo_data fill an EMPTY database. Return the number of added cars."""
    upgrade_database(settings.database_url)
    if not settings.seed_demo_data:
        return 0
    engine = create_database_engine(settings.database_url)
    try:
        with create_session_factory(engine)() as session:
            if ManufacturerRepository(session).get_all():
                return 0  # data are already there: nothing is added twice
            return seed_catalog(session)
    finally:
        engine.dispose()


def main() -> int:
    """Start the service; return the exit code."""
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info(
        "Starting %s %s: environment=%s, log level=%s",
        settings.app_name,
        __version__,
        settings.environment,
        settings.log_level,
    )
    added = prepare_database(settings)
    logger.info("Database migrations applied; demo cars added: %s", added)
    uvicorn.run(
        "car_catalog.api:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.environment == "development",  # restart on code changes only in development
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
