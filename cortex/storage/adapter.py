"""
CORTEX v6.0 — StorageAdapter Protocol.

Unified interface that abstracts all read/write operations from the engine.
All storage backends (SQLite, PostgreSQL, Turso) must implement this protocol
so CortexEngine never knows which backend is active.

Design invariants:
- Protocol is runtime_checkable — adapters are verified at init time.
- commit() is part of the contract; no-op for auto-commit backends (asyncpg).
- health_check() must always return bool, never raise.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

__all__ = ["StorageAdapter"]


@runtime_checkable
class StorageAdapter(Protocol):
    """Structural protocol for all CORTEX storage backends.

    Implementations must provide these async methods to be
    compatible with CortexEngine and all mixin layers.
    """

    async def get_conn(self) -> Any:
        """Return the underlying connection or pool object. Used for backward compatibility."""
        ...

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        """Execute a statement. Return implementation-defined result (e.g. cursor or None)."""
        ...

    async def fetch_all(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        """Execute a query and return all rows as a list of dicts."""
        ...

    async def fetch_one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        """Execute a query and return the first row as a dict, or None."""
        ...

    async def execute_insert(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        """Execute an INSERT and return the inserted row ID."""
        ...

    async def executemany(self, sql: str, params_list: list[tuple[Any, ...]]) -> None:
        """Execute a statement with multiple parameter sets (batch)."""
        ...

    async def executescript(self, script: str) -> None:
        """Execute a multi-statement SQL script."""
        ...

    async def commit(self) -> None:
        """Commit the current transaction. No-op for auto-commit backends."""
        ...

    async def rollback(self) -> None:
        """Rollback the current transaction. No-op for auto-commit backends."""
        ...

    async def close(self) -> None:
        """Release all connections and resources."""
        ...

    async def health_check(self) -> bool:
        """Verify backend connectivity. Never raises — always returns bool."""
        ...
