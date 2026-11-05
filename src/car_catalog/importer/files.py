"""File helpers: atomic writer, retry of file access and logged operation."""

import gzip
import logging
import shutil
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from types import TracebackType
from typing import TextIO, TypeVar

from car_catalog.importer.exceptions import ApplicationError

T = TypeVar("T")

logger = logging.getLogger(__name__)


def open_input(path: Path) -> TextIO:
    """Open a text file for reading; .gz files are decompressed on the fly."""
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return path.open(encoding="utf-8", newline="")


def retry(action: Callable[[], T], *, attempts: int = 3, delay: float = 0.1) -> T:
    """Call action again if a temporary file access error (PermissionError) occurs."""
    for attempt in range(1, attempts + 1):
        try:
            return action()
        except PermissionError as error:
            if attempt == attempts:
                raise
            logger.warning("Спроба %s з %s невдала: %s", attempt, attempts, error)
            time.sleep(delay)
    raise ValueError("attempts має бути більшим за 0")


def backup_path(path: Path) -> Path:
    """Return the path of the backup copy of an output file."""
    return path.with_name(path.name + ".bak")


class AtomicWriter:
    """Transaction-like file write: commit on success, rollback on error."""

    def __init__(self, path: Path, *, backup: bool = False) -> None:
        self.path = path
        self.temporary = path.with_name(path.name + ".tmp")
        self.backup = backup
        self.file: TextIO | None = None

    def __enter__(self) -> TextIO:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.suffix == ".gz":
            self.file = gzip.open(self.temporary, "wt", encoding="utf-8", newline="")
        else:
            self.file = self.temporary.open("w", encoding="utf-8", newline="")
        return self.file

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self.file is not None:
            self.file.close()
        if exc_type is not None:
            self.rollback()
            return
        try:
            if self.backup and self.path.exists():
                shutil.copy2(self.path, backup_path(self.path))
            self.temporary.replace(self.path)
        except OSError:
            self.rollback()
            raise

    def rollback(self) -> None:
        """Delete the temporary file; the previous output stays unchanged."""
        self.temporary.unlink(missing_ok=True)
        logger.warning("Запис %s скасовано, тимчасовий файл видалено", self.path)


@contextmanager
def logged_operation(operation: str) -> Iterator[None]:
    """Log start, duration and failure of an operation."""
    logger.info("%s: початок", operation)
    start = time.perf_counter()
    try:
        yield
    except ApplicationError as error:
        logger.error("%s: перервано (%s: %s)", operation, type(error).__name__, error)
        raise
    except Exception:
        logger.exception("%s: неочікувана помилка", operation)
        raise
    else:
        logger.info("%s: завершено за %.6f с", operation, time.perf_counter() - start)
