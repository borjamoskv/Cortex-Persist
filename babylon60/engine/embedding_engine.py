# [C5-REAL] Exergy-Maximized
"""
Embedding Engine - Asynchronous fact embedding and Specular Memory.
Ω₁: G10 Specular Memory (HDC-Native).
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3

# --- C5-REAL BFT PATCH (R10) ---
import sqlite3 as _sqlite3_bft_orig
_orig_sqlite_connect = _sqlite3_bft_orig.connect
def _bft_sqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    conn = _orig_sqlite_connect(*args, **kwargs)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn
_sqlite3_bft_orig.connect = _bft_sqlite_connect
# -------------------------------
from typing import Any, Protocol

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


class EmbedderProtocol(Protocol):
    def embed(self, text: str) -> Any: ...


class HDCEncoderProto(Protocol):
    def encode_text(self, text: str) -> Any: ...


class HDCMemoryProto(Protocol):
    async def memorize(self, fact: Any) -> None: ...


class MemoryManagerProtocol(Protocol):
    _hdc_encoder: HDCEncoderProto | None
    _hdc: HDCMemoryProto | None

    def get_context_vector(self) -> Any: ...


logger = logging.getLogger("cortex")


async def embed_fact_async(
    conn: aiosqlite.Connection,
    fact_id: int,
    project: str,
    content: str,
    embedder: EmbedderProtocol | None = None,
    memory_manager: MemoryManagerProtocol | None = None,
    tenant_id: str = "default",
) -> None:
    """Generate and store embedding for a fact asynchronously."""
    # 1. Legacy Vector Store (L2 Dense)
    if embedder:
        try:
            import inspect

            if inspect.iscoroutinefunction(embedder.embed):
                embedding = await embedder.embed(content)
            else:
                embedding = await asyncio.to_thread(embedder.embed, content)
            await conn.execute(
                "INSERT INTO fact_embeddings (fact_id, embedding) VALUES (?, ?)",
                (fact_id, json.dumps(embedding)),
            )
        except (sqlite3.Error, OSError, ValueError) as e:
            logger.warning("Embedding failed for fact %d: %s", fact_id, e)

    # 2. Vector Alpha (G10 Specular Memory)
    if (
        memory_manager
        and hasattr(memory_manager, "get_context_vector")
        and memory_manager._hdc_encoder
    ):
        try:
            import numpy as np

            from babylon60.memory.hdc.algebra import bind
            from babylon60.memory.models import CortexFactModel

            fact_hv = memory_manager._hdc_encoder.encode_text(content)
            context_hv = memory_manager.get_context_vector()

            if context_hv is not None:
                intent_hv = bind(fact_hv, context_hv)
                specular_bytes = np.array(intent_hv, dtype=np.float32).tobytes()
                await conn.execute(
                    "INSERT INTO specular_embeddings (fact_id, embedding) VALUES (?, ?)",
                    (fact_id, specular_bytes),
                )
                logger.debug("Specular Memory indexed for fact %d", fact_id)

                if memory_manager._hdc:
                    fact = CortexFactModel(
                        id=str(fact_id),
                        tenant_id=tenant_id,
                        project_id=project,
                        content=content,
                        embedding=fact_hv.tolist(),
                        specular_embedding=intent_hv.tolist(),
                    )
                    await memory_manager._hdc.memorize(fact)
                    logger.debug("Vector Alpha (HDC) indexed for fact %d", fact_id)
        except (
            sqlite3.Error,
            aiosqlite.Error,
            OSError,
            ValueError,
            AttributeError,
            TypeError,
        ) as e:
            logger.warning("Specular Memory indexing failed for fact %d: %s", fact_id, e)
