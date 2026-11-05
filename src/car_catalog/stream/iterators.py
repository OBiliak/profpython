"""Custom iterator class and infinite generator of car IDs."""

from collections.abc import Iterator
from itertools import count


class CarIdRange:
    """Iterator over car IDs from start to stop inclusive."""

    def __init__(self, start: int, stop: int) -> None:
        """Remember the current ID and the last ID."""
        self.current = start
        self.stop = stop

    def __iter__(self) -> "CarIdRange":
        """Return the iterator itself."""
        return self

    def __next__(self) -> int:
        """Return the next ID or raise StopIteration after the last one."""
        if self.current > self.stop:
            raise StopIteration
        value = self.current
        self.current += 1
        return value


def generate_ids(start: int = 1) -> Iterator[int]:
    """Yield car IDs without end, starting from start."""
    yield from count(start)
