"""Errors of the persistence layer."""

from car_catalog.domain.exceptions import CatalogError


class DatabaseConstraintError(CatalogError):
    """Raised when the database rejects data (UNIQUE, CHECK or FOREIGN KEY constraint)."""


class PriceUpdateError(CatalogError, ValueError):
    """Raised when a bulk price update has incorrect data; the transaction is rolled back."""
