"""CORTEX v5.1 — Sovereign Write Worker: Internal Message Types.

Extracted from db_writer.py to keep file size under 400 LOC.
Contains the internal message dataclasses and TransactionProxy used
by the SqliteWriteWorker queue.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from cortex.utils.result import Result

if TYPE_CHECKING:
    from cortex.database.writer import SqliteWriteWorker

__all__ = [
    "TransactionProxy",
    "_Message",
    "_Shutdown",
    "_TxBegin",
    "_TxCommit",
    "_TxRollback",
    "_WriteOp",
]


@dataclass(frozen=True, slots=True)
class _WriteOp:
    """A single write operation to be processed by the worker."""

    sql: str
    params: tuple[Any, ...] = ()
    future: asyncio.Future[Result[int, str]] = field(
        default_factory=lambda: asyncio.get_event_loop().create_future()
    )


@dataclass(frozen=True, slots=True)
class _TxBegin:
    """Signal to begin a transaction."""

    future: asyncio.Future[Result[None, str]] = field(
        default_factory=lambda: asyncio.get_event_loop().create_future()
    )


@dataclass(frozen=True, slots=True)
class _TxCommit:
    """Signal to commit the current transaction."""

    future: asyncio.Future[Result[None, str]] = field(
        default_factory=lambda: asyncio.get_event_loop().create_future()
    )


@dataclass(frozen=True, slots=True)
class _TxRollback:
    """Signal to rollback the current transaction."""

    future: asyncio.Future[Result[None, str]] = field(
        default_factory=lambda: asyncio.get_event_loop().create_future()
    )


@dataclass(frozen=True, slots=True)
class _Shutdown:
    """Poison pill to stop the writer loop."""

    future: asyncio.Future[Result[None, str]] = field(
        default_factory=lambda: asyncio.get_event_loop().create_future()
    )


_Message = _WriteOp | _TxBegin | _TxCommit | _TxRollback | _Shutdown


class TransactionProxy:
    """Proxy for transactional writes within a writer context."""

    def __init__(self, worker: SqliteWriteWorker):
        self._worker = worker

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> Result[int, str]:
        """Execute a write within the active transaction."""
        return await self._worker.execute(sql, params)
