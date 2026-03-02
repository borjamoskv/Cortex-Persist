"""Fact Sovereign Layer — FactManager for CORTEX."""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

from pydantic import BaseModel, Field

from cortex.engine.models import Fact, row_to_fact
from cortex.memory.temporal import build_temporal_filter_params, now_iso

__all__ = ["FactManager"]

logger = logging.getLogger("cortex.facts")

_FACT_COLUMNS = (
    "f.id, f.tenant_id, f.project, f.content, f.fact_type, f.tags, f.confidence, "
    "f.valid_from, f.valid_until, f.source, f.meta, f.consensus_score, "
    "f.created_at, f.updated_at, f.tx_id, t.hash"
)
_FACT_JOIN = "FROM facts f LEFT JOIN transactions t ON f.tx_id = t.id"


class IngestionFact(BaseModel):
    """V8 Guardrail: Strict input validation before processing."""

    project: str = Field(..., min_length=1)
    content: str = Field(..., min_length=10)
    tenant_id: str = Field(..., min_length=1)
    confidence: str = Field(..., pattern=r"^(C[1-5]|stated|inferred)$")
    # Mapping 'source' parameter to 'provenance' conceptually
    source: str = Field(..., min_length=1, description="Provenance / Data origin")


class FactManager:
    """Manages the full lifecycle and retrieval of facts."""

    def __init__(self, engine):
        self.engine = engine

    # Minimum content length to prevent garbage facts.
    MIN_CONTENT_LENGTH = 10

    async def store(
        self,
        project: str,
        content: str,
        tenant_id: str = "default",
        fact_type: str = "knowledge",
        tags: list[str] | None = None,
        confidence: str = "stated",
        source: str | None = None,
        meta: dict[str, Any] | None = None,
        valid_from: str | None = None,
        commit: bool = True,
        tx_id: int | None = None,
        conn: Any | None = None,
        **kwargs,
    ) -> int:
        """Sovereign Store: Delegates to engine with pre-validation."""
        conn = conn or await self.engine.get_conn()

        # Sovereign Pre-filtering Gate: Active Forgetting (#350/100)
        if (
            hasattr(self.engine, "memory")
            and self.engine.memory
            and hasattr(self.engine.memory, "thalamus")
        ):
            should_process, action, _ = await self.engine.memory.thalamus.filter(
                content=content, project_id=project, tenant_id=tenant_id, fact_type=fact_type
            )
            if not should_process:
                from cortex.routes.notch_ws import notify_notch_pruning

                await notify_notch_pruning()
                raise ValueError(f"Thalamus: Fact rejected ({action})")

        # V8 Validation Layer (Strict Pydantic)
        try:
            validated = IngestionFact(
                project=project,
                content=content,
                tenant_id=tenant_id,
                confidence=confidence,
                source=source or "cli",
            )
            # Re-assign validated properties just in case of coerced changes
            project = validated.project
            content = validated.content
            tenant_id = validated.tenant_id
            confidence = validated.confidence
            source = validated.source

            # V8 Semantic Deduplication
            if hasattr(self.engine, "embeddings") and self.engine.embeddings:
                # 1. Generate text embedding
                if hasattr(self.engine.embeddings, "embed_text"):
                    vec = await self.engine.embeddings.embed_text(content)
                    if vec:
                        # 2. Check for Similarity > 0.90 in sqlite-vec facts or embeddings
                        # Since we only evaluate, if the result is high, skip store
                        results = await self.search(
                            query=content, tenant_id=tenant_id, project=project, top_k=1
                        )
                        if results and results[0].score > 0.90:
                            logger.info(
                                "V8 Guardrail: Fact discarded - Semantic Duplicate of "
                                f"#{results[0].fact_id} (Score: {results[0].score:.2f})"
                            )
                            # We update updated_at / last_accessed
                            await conn.execute(
                                "UPDATE facts SET updated_at = ? WHERE id = ?",
                                (now_iso(), results[0].fact_id),
                            )
                            await conn.commit()
                            return results[0].fact_id
        except Exception as e:
            from pydantic import ValidationError

            if isinstance(e, ValidationError):
                raise ValueError(f"Ingestion Validation Failed: {e}") from e
            logger.warning(f"V8 Deduplication check skipped or failed: {e}")

        from cortex.engine.store_mixin import StoreMixin

        return await StoreMixin._store_impl(
            self.engine,
            conn,
            project,
            content,
            tenant_id,
            fact_type,
            tags,
            confidence,
            source,
            meta,
            valid_from,
            commit,
            tx_id,
        )

    async def store_many(self, facts: list[dict]) -> list[int]:
        if not facts:
            raise ValueError("Facts list cannot be empty")

        # Validation pass before any inserts
        for i, fact in enumerate(facts):
            if "project" not in fact or not fact["project"].strip():
                raise ValueError(f"Fact at index {i} is missing project")
            if "content" not in fact or not fact["content"].strip():
                raise ValueError(f"Fact at index {i} is missing content")

        conn = await self.engine.get_conn()
        ids = []
        try:
            for fact in facts:
                tenant_id = fact.get("tenant_id", "default")
                fid = await self.store(
                    project=fact["project"],
                    content=fact["content"],
                    tenant_id=tenant_id,
                    fact_type=fact.get("fact_type", "knowledge"),
                    tags=fact.get("tags"),
                    confidence=fact.get("confidence", "stated"),
                    source=fact.get("source"),
                    meta=fact.get("meta"),
                    valid_from=fact.get("valid_from"),
                    commit=False,
                )
                ids.append(fid)
            await conn.commit()
            return ids
        except (sqlite3.Error, OSError, ValueError):
            await conn.rollback()
            raise

    async def get_fact(self, fact_id: int) -> Fact | None:
        """Retrieve any fact by ID, including deprecated ones."""
        conn = await self.engine.get_conn()
        cursor = await conn.execute(
            f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} WHERE f.id = ?", (fact_id,)
        )
        row = await cursor.fetchone()
        return row_to_fact(row) if row else None

    async def _fetch(self, query: str, params: list | tuple = ()) -> list[Fact]:
        conn = await self.engine.get_conn()
        cursor = await conn.execute(query, params)
        return [row_to_fact(r) for r in await cursor.fetchall()]

    async def get_all_active_facts(
        self,
        tenant_id: str = "default",
        project: str | None = None,
        fact_types: list[str] | None = None,
    ) -> list[Fact]:
        q = f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} WHERE f.tenant_id = ? AND f.valid_until IS NULL AND f.is_quarantined = 0 AND f.is_tombstoned = 0"
        p = [tenant_id]
        if project:
            q += " AND f.project = ?"
            p.append(project)
        if fact_types:
            q += f" AND f.fact_type IN ({','.join('?' * len(fact_types))})"
            p.extend(fact_types)
        return await self._fetch(q + " ORDER BY f.project, f.fact_type, f.id", p)

    async def recall(
        self, project: str, tenant_id: str = "default", limit: int | None = None, offset: int = 0
    ) -> list[Fact]:
        q = (
            f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} WHERE f.tenant_id = ? AND f.project = ? AND f.valid_until IS NULL "
            f"AND f.is_quarantined = 0 AND f.is_tombstoned = 0 ORDER BY (f.consensus_score * 0.8 + "
            f"(1.0 / (1.0 + (julianday('now') - julianday(f.created_at)))) * 0.2) DESC, f.fact_type, f.created_at DESC"
        )
        p = [tenant_id, project]
        if limit:
            q += " LIMIT ?"
            p.append(limit)
        if offset:
            q += " OFFSET ?"
            p.append(offset)
        return await self._fetch(q, p)

    async def history(
        self, project: str, tenant_id: str = "default", as_of: str | None = None
    ) -> list[Fact]:
        if as_of:
            c, p = build_temporal_filter_params(as_of, table_alias="f")
            return await self._fetch(
                f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} WHERE f.tenant_id=? AND f.project=? AND f.is_tombstoned=0 AND {c} ORDER BY f.valid_from DESC",
                [tenant_id, project] + p,
            )
        return await self._fetch(
            f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} WHERE f.tenant_id=? AND f.project=? AND f.is_tombstoned=0 ORDER BY f.valid_from DESC",
            [tenant_id, project],
        )

    async def time_travel(
        self, tx_id: int, tenant_id: str = "default", project: str | None = None
    ) -> list[Fact]:
        from cortex.memory.temporal import time_travel_filter

        c, p = time_travel_filter(tx_id, table_alias="f")
        q = f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} WHERE f.tenant_id = ? AND f.is_tombstoned = 0 AND {c}"
        p = [tenant_id] + p
        if project:
            q += " AND f.project = ?"
            p.append(project)
        return await self._fetch(q + " ORDER BY f.id ASC", p)

    reconstruct_state = time_travel

    async def register_ghost(self, reference: str, context: str, project: str) -> int:
        conn = await self.engine.get_conn()
        c = await conn.execute(
            "SELECT id FROM ghosts WHERE reference=? AND project=?", (reference, project)
        )
        if r := await c.fetchone():
            return r[0]
        c = await conn.execute(
            "INSERT INTO ghosts (reference, context, project, status, created_at) VALUES (?, ?, ?, 'open', ?)",
            (reference, context, project, now_iso()),
        )
        await conn.commit()
        return c.lastrowid

    async def stats(self) -> dict:
        conn = await self.engine.get_conn()
        res = {
            "total_facts": (await (await conn.execute("SELECT COUNT(*) FROM facts")).fetchone())[0]
        }
        res["active_facts"] = (
            await (
                await conn.execute("SELECT COUNT(*) FROM facts WHERE valid_until IS NULL")
            ).fetchone()
        )[0]
        res["deprecated_facts"] = res["total_facts"] - res["active_facts"]
        res["projects"] = [
            p[0]
            for p in await (
                await conn.execute("SELECT DISTINCT project FROM facts WHERE valid_until IS NULL")
            ).fetchall()
        ]
        res["project_count"] = len(res["projects"])
        res["types"] = dict(
            await (
                await conn.execute(
                    "SELECT fact_type, COUNT(*) FROM facts WHERE valid_until IS NULL GROUP BY fact_type"
                )
            ).fetchall()
        )
        res["transactions"] = (
            await (await conn.execute("SELECT COUNT(*) FROM transactions")).fetchone()
        )[0]
        res["db_path"], res["db_size_mb"] = (
            str(self.engine._db_path),
            round(self.engine._db_path.stat().st_size / (1024 * 1024), 2)
            if self.engine._db_path.exists()
            else 0,
        )
        try:
            res["embeddings"] = (
                await (await conn.execute("SELECT COUNT(*) FROM fact_embeddings")).fetchone()
            )[0]
        except Exception:
            res["embeddings"] = 0
        return res

    def __getattr__(self, name: str) -> Any:
        """Sovereign Ablation (Wave 5): Proxy to decouple Calcification."""
        if name in ("search", "update", "deprecate"):
            return getattr(self.engine, name)
        GM = {
            "graph": "get_graph",
            "query_entity": "query_entity",
            "find_path": "find_path",
            "get_context_subgraph": "get_context_subgraph",
        }
        if name in GM:

            async def _g_proxy(*args, **kwargs):
                import cortex.graph

                return await getattr(cortex.graph, GM[name])(
                    await self.engine.get_conn(), *args, **kwargs
                )

            return _g_proxy
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
