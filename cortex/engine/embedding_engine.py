"""
Embedding Engine - Asynchronous fact embedding and Specular Memory.
Ω₁: G10 Specular Memory (HDC-Native).
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from typing import Any, Protocol

import aiosqlite

from cortex.memory.vector_store import VectorStore


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
    vector_store: VectorStore | None = None,
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
            
            if vector_store:
                await vector_store.upsert(tenant_id, fact_id, embedding, payload={"project": project})
            else:
                # Fallback to local sqlite vec virtual table if no external vector store provided
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

            from cortex.memory.hdc.algebra import bind
            from cortex.memory.models import CortexFactModel

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
