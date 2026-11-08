"""Database engine and session factory of the car catalog (SQLite + SQLAlchemy)."""

from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from car_catalog.config import get_settings

DATABASE_PATH = "car_catalog.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"


def database_url() -> str:
    """URL of the working database from the settings (environment variable DATABASE_URL)."""
    return get_settings().database_url


def enable_foreign_keys(dbapi_connection: Any, connection_record: Any) -> None:
    """Turn on FOREIGN KEY checks: SQLite keeps them off for every new connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


def create_database_engine(database_url: str = DATABASE_URL) -> Engine:
    """Create an engine whose connections check foreign keys."""
    engine = create_engine(database_url, echo=False)
    event.listen(engine, "connect", enable_foreign_keys)
    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a factory of sessions bound to the engine."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


engine = create_database_engine()
SessionLocal = create_session_factory(engine)
