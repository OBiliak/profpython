"""Streaming readers: lines of one or several files without loading them into memory."""

from collections.abc import Iterable, Iterator
from itertools import chain
from pathlib import Path


def read_lines(path: Path) -> Iterator[str]:
    """Yield lines of a text file one by one."""
    with path.open(encoding="utf-8") as file:
        yield from file


def read_many_files(paths: Iterable[Path]) -> Iterator[str]:
    """Yield lines of several files as one stream."""
    return chain.from_iterable(read_lines(path) for path in paths)
