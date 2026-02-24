# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.1 — Railway Oriented Programming (Result Monads).

Sovereign implementation of the Result pattern for deterministic error flow.
Replaces exception-based control flow in liminal layers (LLM <-> Engine <-> MCP).

Usage:
    from cortex.result import Ok, Err, Result

    def parse_agent_output(raw: str) -> Result[dict, str]:
        try:
            data = json.loads(raw)
            return Ok(data)
        except json.JSONDecodeError as e:
            return Err(f"JSON decode failed: {e}")

    # Chain operations without try/except:
    result = parse_agent_output(llm_response)
    match result:
        case Ok(data):
            process(data)
        case Err(error):
            feed_back_to_llm(error)
"""

from __future__ import annotations

import traceback
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

__all__ = ["Ok", "Err", "Result", "safe", "safe_async"]

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")


@dataclass(frozen=True, slots=True)
class Ok(Generic[T]):
    """Success track of the railway. Immutable, zero-cost wrapper."""

    value: T

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def unwrap(self) -> T:
        """Extract the value. Safe to call on Ok."""
        return self.value

    def unwrap_or(self, default: T) -> T:  # type: ignore[override]
        return self.value

    def map(self, fn: Callable[[T], U]) -> Result[U, Any]:
        """Apply fn to the value, stay on success track."""
        return Ok(fn(self.value))

    def flat_map(self, fn: Callable[[T], Result[U, Any]]) -> Result[U, Any]:
        """Monadic bind — apply fn that returns a Result."""
        return fn(self.value)

    def map_err(self, _fn: Callable[[Any], Any]) -> Ok[T]:
        """No-op on success track."""
        return self

    def __repr__(self) -> str:
        return f"Ok({self.value!r})"


@dataclass(frozen=True, slots=True)
class Err(Generic[E]):
    """Failure track of the railway. Carries structured error info."""

    error: E

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def unwrap(self) -> Any:
        """Raise on Err — forces explicit handling."""
        raise ValueError(f"Called unwrap() on Err: {self.error}")

    def unwrap_or(self, default: Any) -> Any:
        return default

    def map(self, _fn: Callable) -> Err[E]:
        """No-op on failure track."""
        return self

    def flat_map(self, _fn: Callable) -> Err[E]:
        """No-op on failure track."""
        return self

    def map_err(self, fn: Callable[[E], U]) -> Err[U]:
        """Transform the error, stay on failure track."""
        return Err(fn(self.error))

    def __repr__(self) -> str:
        return f"Err({self.error!r})"


# Union type for pattern matching and type narrowing
Result = Ok[T] | Err[E]


def safe(fn: Callable[..., T]) -> Callable[..., Result[T, str]]:
    """Decorator: wraps a sync function to return Result instead of raising."""

    def wrapper(*args: Any, **kwargs: Any) -> Result[T, str]:
        try:
            return Ok(fn(*args, **kwargs))
        except Exception as exc:  # deliberate boundary — @safe wraps any callable
            tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
            return Err(f"{type(exc).__name__}: {exc}\n{''.join(tb[-3:])}")

    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    return wrapper


def safe_async(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator: wraps an async function to return Result instead of raising."""

    async def wrapper(*args: Any, **kwargs: Any) -> Result[T, str]:
        try:
            return Ok(await fn(*args, **kwargs))
        except Exception as exc:  # deliberate boundary — @safe_async wraps any async callable
            tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
            return Err(f"{type(exc).__name__}: {exc}\n{''.join(tb[-3:])}")

    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    return wrapper
