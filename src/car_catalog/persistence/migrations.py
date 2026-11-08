"""Apply Alembic migrations from Python (the same as `alembic upgrade head`)."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Engine

# migrations are a part of the package, so they are also in the wheel and in the Docker image
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def make_alembic_config(database_url: str) -> Config:
    """Alembic configuration without alembic.ini: migrations of the package and the database URL."""
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.set_main_option("sqlalchemy.url", database_url)
    config.attributes["configure_logger"] = False
    return config


def upgrade_database(database_url: str, revision: str = "head") -> None:
    """Apply migrations up to the revision."""
    command.upgrade(make_alembic_config(database_url), revision)


def downgrade_database(database_url: str, revision: str) -> None:
    """Cancel migrations down to the revision."""
    command.downgrade(make_alembic_config(database_url), revision)


def current_revision(engine: Engine) -> str | None:
    """Revision stored in the table alembic_version."""
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()
