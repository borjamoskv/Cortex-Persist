"""
CORTEX — Thread-Safe Singleton Pattern.
Ensures a single instance per process even under high concurrency.
"""

from __future__ import annotations

import threading
from typing import Any, TypeVar

T = TypeVar("T")


class ThreadSafeSingleton(type):
    """Metaclass for Thread-Safe Singleton using double-checked locking."""

    _instances: dict[type[Any], Any] = {}
    _lock = threading.Lock()

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


def reset_singleton(cls: type[Any]) -> None:
    """Utility to reset a singleton instance (mainly for tests)."""
    with ThreadSafeSingleton._lock:
        if cls in ThreadSafeSingleton._instances:
            del ThreadSafeSingleton._instances[cls]
