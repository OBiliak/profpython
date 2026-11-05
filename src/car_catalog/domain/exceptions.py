"""Custom exception hierarchy of the car catalog domain."""


class CatalogError(Exception):
    """Base error of the car catalog domain."""


class EntityNotFoundError(CatalogError):
    """Raised when an item with the given ID does not exist in a repository."""

    def __init__(self, item_id: int) -> None:
        super().__init__(f"Запис з ID {item_id} не знайдено.")
        self.item_id = item_id


class DuplicateEntityError(CatalogError):
    """Raised when an item with the same ID is already stored in a repository."""

    def __init__(self, item_id: int) -> None:
        super().__init__(f"Запис з ID {item_id} вже існує.")
        self.item_id = item_id


class EmptyCatalogError(CatalogError):
    """Raised when a statistic is requested for an empty catalog."""

    def __init__(self) -> None:
        super().__init__("Каталог порожній.")


class InvalidVehicleError(CatalogError, ValueError):
    """Raised when vehicle data is not valid."""
