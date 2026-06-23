# [C5-REAL] Exergy-Maximized — FPU Eradication Runtime Guard
# Author: Borja Moskv (borjamoskv)
"""Runtime float type interception for BABYLON-60 enforcement.

Provides:
- FPUFirewall: Static methods for guarding function boundaries against float infiltration.
- @no_float: Decorator that enforces zero-float at function boundaries.
"""

from __future__ import annotations

import functools
import logging
from typing import Any, TypeVar

logger = logging.getLogger("babylon60.math.fpu_interceptor")

__all__ = ["FPUFirewall", "no_float", "FPUViolationError"]

F = TypeVar("F")


class FPUViolationError(TypeError):
    """Raised when float infiltrates a BABYLON-60 boundary."""

    def __init__(self, context: str, value: Any) -> None:
        self.context = context
        self.value = value
        super().__init__(f"FPU VIOLATION [P0]: {context} — got float({value}). Use Babylon60.")


class FPUFirewall:
    """Static boundary guard. Intercepts float at function entry/exit."""

    @staticmethod
    def guard_args(func_name: str, /, **kwargs: Any) -> None:
        """Reject any float-typed keyword arguments."""
        for name, value in kwargs.items():
            if isinstance(value, float):
                raise FPUViolationError(f"{func_name}('{name}')", value)

    @staticmethod
    def guard_positional(func_name: str, args: tuple[Any, ...]) -> None:
        """Reject any float-typed positional arguments."""
        for i, value in enumerate(args):
            if isinstance(value, float):
                raise FPUViolationError(f"{func_name}(arg[{i}])", value)

    @staticmethod
    def guard_return(value: Any, func_name: str) -> Any:
        """Reject float return values."""
        if isinstance(value, float):
            raise FPUViolationError(f"{func_name}() returned", value)
        return value

    @staticmethod
    def guard_dict(data: dict[str, Any], context: str) -> None:
        """Reject any float values in a dictionary (e.g., metadata)."""
        for key, value in data.items():
            if isinstance(value, float):
                raise FPUViolationError(f"{context}['{key}']", value)

    @staticmethod
    def guard_iterable(items: Any, context: str) -> None:
        """Reject float values in any iterable."""
        for i, item in enumerate(items):
            if isinstance(item, float):
                raise FPUViolationError(f"{context}[{i}]", item)


def no_float(func: F) -> F:
    """Decorator: enforces zero-float at function boundaries.

    Checks all positional and keyword arguments on entry.
    Checks return value on exit.
    Raises FPUViolationError on any float detection.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Guard entry
        FPUFirewall.guard_positional(func.__qualname__, args)
        FPUFirewall.guard_args(func.__qualname__, **kwargs)
        # Execute
        result = func(*args, **kwargs)
        # Guard exit
        FPUFirewall.guard_return(result, func.__qualname__)
        return result

    return wrapper  # type: ignore[return-value]
