# [C5-REAL] Exergy-Maximized
"""Permanent pytest tests for parent_decision_id causal infrastructure.

Covers:
- Phase 1: Data model, SQL roundtrip, schema index
- Phase 2: Type reconciliation, FK validation, auto-resolve (decision)
- Phase 3: Auto-resolve (error), get_causal_chain API, CLI integration
- Phase 5: MCP tool params, sync wrappers
"""

from __future__ import annotations

import base64
import os

os.environ.setdefault("CORTEX_TESTING", "1")
os.environ.setdefault(
    "CORTEX_MASTER_KEY",
    base64.b64encode(os.urandom(32)).decode(),
)

import inspect

import aiosqlite

# --- C5-REAL BFT PATCH AIOSQLITE (R10) ---
import aiosqlite as _aiosqlite_bft_orig
_orig_aiosqlite_connect = _aiosqlite_bft_orig.connect
def _bft_aiosqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    class BFTConnectionContext:
        def __init__(self, *args, **kwargs):
            self._conn_future = _orig_aiosqlite_connect(*args, **kwargs)
        async def __aenter__(self):
            self.conn = await self._conn_future.__aenter__()
            await self.conn.execute("PRAGMA journal_mode=WAL;")
            await self.conn.execute("PRAGMA busy_timeout=5000;")
            await self.conn.execute("PRAGMA synchronous=NORMAL;")
            return self.conn
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self._conn_future.__aexit__(exc_type, exc_val, exc_tb)
        def __await__(self):
            async def _init():
                conn = await self._conn_future
                await conn.execute("PRAGMA journal_mode=WAL;")
                await conn.execute("PRAGMA busy_timeout=5000;")
                await conn.execute("PRAGMA synchronous=NORMAL;")
                return conn
            return _init().__await__()
    return BFTConnectionContext(*args, **kwargs)
_aiosqlite_bft_orig.connect = _bft_aiosqlite_connect
# ----------------------------------------
import pytest

from babylon60.engine.fact_store_core import insert_fact_record
from babylon60.engine.mixins.base import FACT_COLUMNS
from babylon60.engine.models import Fact
from babylon60.engine.query_mixin import QueryMixin


class TestTypeReconciliation:
    """CortexFactModel uses int | None, not str | None."""

    def test_memory_model_type(self):
        import typing

        from babylon60.memory.models import CortexFactModel

        field = CortexFactModel.model_fields["parent_decision_id"]
        args = typing.get_args(field.annotation)
        if args:
            assert int in args
            assert str not in args
