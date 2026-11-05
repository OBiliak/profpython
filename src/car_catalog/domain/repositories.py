"""Generic repository abstraction, in-memory repository and unit of work."""

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Generic, TypeVar

from car_catalog.domain.exceptions import DuplicateEntityError, EntityNotFoundError
from car_catalog.domain.protocols import HasId

T = TypeVar("T", bound=HasId)


class Repository(ABC, Generic[T]):
    """Abstract storage of items with an integer ID."""

    @abstractmethod
    def add(self, item: T) -> None:
        """Store a new item."""

    @abstractmethod
    def find(self, item_id: int) -> T | None:
        """Return an item by ID or None."""

    @abstractmethod
    def all(self) -> list[T]:
        """Return all items."""

    @abstractmethod
    def remove(self, item_id: int) -> None:
        """Delete an item by ID."""

    def get(self, item_id: int) -> T:
        """Return an item by ID or raise EntityNotFoundError."""
        item = self.find(item_id)
        if item is None:
            raise EntityNotFoundError(item_id)
        return item


class InMemoryRepository(Repository[T]):
    """Repository that keeps items in a dict by ID."""

    def __init__(self) -> None:
        self._items: dict[int, T] = {}

    def add(self, item: T) -> None:
        """Store a new item or raise DuplicateEntityError."""
        if item.id in self._items:
            raise DuplicateEntityError(item.id)
        self._items[item.id] = item

    def find(self, item_id: int) -> T | None:
        """Return an item by ID or None."""
        return self._items.get(item_id)

    def all(self) -> list[T]:
        """Return all items in the order of adding."""
        return list(self._items.values())

    def remove(self, item_id: int) -> None:
        """Delete an item or raise EntityNotFoundError."""
        if self._items.pop(item_id, None) is None:
            raise EntityNotFoundError(item_id)

    def __len__(self) -> int:
        """Return the number of stored items."""
        return len(self._items)


class UnitOfWork(Generic[T]):
    """Collects new items and saves them to the repository all at once."""

    def __init__(self, repository: Repository[T]) -> None:
        self.repository = repository
        self._new_items: list[T] = []

    def register_new(self, item: T) -> None:
        """Remember an item that will be saved on commit."""
        self._new_items.append(item)

    def commit(self) -> int:
        """Save all new items if none of them breaks the repository rules."""
        ids = [item.id for item in self._new_items]
        for item_id in ids:
            if ids.count(item_id) > 1 or self.repository.find(item_id) is not None:
                raise DuplicateEntityError(item_id)
        for item in self._new_items:
            self.repository.add(item)
        saved = len(self._new_items)
        self._new_items.clear()
        return saved

    def rollback(self) -> None:
        """Forget all items that were not saved."""
        self._new_items.clear()

    def __enter__(self) -> "UnitOfWork[T]":
        """Start the unit of work in a with block."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Discard unsaved items when the with block ends."""
        self.rollback()
