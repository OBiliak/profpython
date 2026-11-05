"""Decorators for measuring time and logging catalog operations."""

from collections import deque
from collections.abc import Callable
from functools import wraps
from time import perf_counter

operation_history: deque[tuple[str, int]] = deque(maxlen=5)


def measure_time(func: Callable) -> Callable:
    """Print the execution time of the decorated function."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = perf_counter()
        result = func(*args, **kwargs)
        elapsed = perf_counter() - start
        print(f"{func.__name__}: {elapsed:.8f} s")
        return result

    return wrapper


def log_operation(label: str) -> Callable:
    """Save the operation label and the result size to operation_history."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            operation_history.append((label, len(result)))
            return result

        return wrapper

    return decorator
