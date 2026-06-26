# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import dataclasses
import logging
from typing import TYPE_CHECKING, Any, cast

from pydantic import ValidationError

from cortex.engine.cognitive.models import Fact, row_to_fact
from cortex.engine.core.store_validators import validate_content
from cortex.utils.canonical import now_iso

if TYPE_CHECKING:
    from cortex.extensions.interfaces.engine import EngineProtocol

_FACT_FIELDS = {f.name for f in dataclasses.fields(Fact)}

__all__ = ["FactManager"]

logger = logging.getLogger("cortex.facts")

try:
    from cortex.security.haiku import HaikuGuard
except ImportError:
    HaikuGuard = None


class FactManager:
    """Manages the full lifecycle and retrieval of facts."""

    def __init__(self, engine: EngineProtocol):
        self.engine = engine

    @staticmethod
    def _coerce_fact(raw: Fact | dict[str, Any]) -> Fact:
        if isinstance(raw, Fact):
            return raw
        return Fact(**{k: v for k, v in raw.items() if k in _FACT_FIELDS})

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
        tenant_id = self.engine._resolve_tenant(tenant_id)
        if conn:
            return await self._store_delegate(
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
                **kwargs,
            )

        async with self.engine.session() as conn:
            return await self._store_delegate(
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
                **kwargs,
            )

    async def _store_delegate(
        self,
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
        **kwargs,
    ) -> int:
        meta = dict(meta) if meta else {}
        actor_id = kwargs.get("actor_id")
        if source is None and actor_id:
            source = (
                actor_id
                if isinstance(actor_id, str)
                and actor_id.startswith(("agent:", "cli", "api", "human"))
                else f"agent:{actor_id}"
            )
        if source and "source" not in meta:
            meta["source"] = source
        for k, v in kwargs.items():
            if k not in meta:
                meta[k] = v

        # Optional guard: do not block engine startup if the immunity stack is mid-repair.
        if HaikuGuard is not None:
            HaikuGuard.enforce(content, {"fact_type": fact_type, "tags": tags or []})

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

        # V8 Validation Layer (Sovereign Gate)
        try:
            content = validate_content(project, content, fact_type)

            # P0 Thermodynamic Gate: O(1) Exact Match (Axiom Ω₂)
            cursor = await conn.execute(
                "SELECT id FROM facts WHERE content = ? AND project = ? AND tenant_id = ?",
                (content, project, tenant_id),
            )
            row = await cursor.fetchone()
            if row:
                fact_id = row[0]
                logger.info("V8 Guardrail: Fact discarded - P0 Exact Duplicate of #%s", fact_id)
                await conn.execute(
                    "UPDATE facts SET updated_at = ? WHERE id = ?", (now_iso(), fact_id)
                )
                await conn.commit()
                return fact_id

            # V8 Semantic Deduplication
            if (
                fact_type not in ("mafia_node", "telemetry_batch")
                and hasattr(self.engine, "embeddings")
                and self.engine.embeddings
            ):
                # 1. Generate text embedding
                if hasattr(self.engine.embeddings, "embed_text"):
                    vec = await self.engine.embeddings.embed_text(content)
                    if vec:
                        # 2. Check for Similarity > 0.90 in sqlite-vec facts or embeddings
                        results = await self.engine.search(
                            query=content, tenant_id=tenant_id, project=project, top_k=1
                        )
                        if results and results[0].score > 0.90:  # type: ignore[reportAttributeAccessIssue]
                            logger.info(
                                "V8 Guardrail: Fact discarded - Semantic Duplicate of #%s (Score: %.2f)",
                                results[0].fact_id,  # type: ignore[reportAttributeAccessIssue]
                                results[0].score,  # type: ignore[reportAttributeAccessIssue]
                            )
                            # We update updated_at / last_accessed
                            await conn.execute(  # type: ignore[reportOptionalMemberAccess]
                                "UPDATE facts SET updated_at = ? WHERE id = ?",
                                (now_iso(), results[0].fact_id),
                            )
                            await conn.commit()  # type: ignore[reportOptionalMemberAccess]
                            return results[0].fact_id  # type: ignore[reportAttributeAccessIssue]
        except ValidationError as e:
            raise ValueError(f"Ingestion Validation Failed: {e}") from e
        except (OSError, RuntimeError, ValueError) as e:
            logger.warning("V8 Ingestion check failed: %s", e)

        from cortex.engine.core.store_mixin import StoreMixin

        started_tx = False
        if not conn.in_transaction:
            await conn.execute("BEGIN IMMEDIATE")
            started_tx = True

        try:
            return await StoreMixin._store_impl(
                cast("StoreMixin", self.engine),
                conn,  # type: ignore[reportArgumentType]
                project,
                content,
                tenant_id,
                fact_type,
                tags,
                confidence,
                source,
                actor_id,
                meta,
                valid_from,
                commit,
                tx_id,
            )
        except Exception as e:
            import logging
            log = logging.getLogger(__name__)
            log.error(f"EXCEPTION IN _store_delegate: {type(e).__name__} - started_tx={started_tx}, in_transaction={conn.in_transaction}")
            if started_tx and conn.in_transaction:
                log.error("ROLLING BACK NOW")
                await conn.rollback()
            else:
                log.error("SKIPPING ROLLBACK")
            raise

    async def store_many(self, facts: list[dict]) -> list[int]:
        if not facts:
            raise ValueError("Facts list cannot be empty")
        return await self.engine.store_many(facts)

    async def get_fact(self, fact_id: int) -> Fact | None:
        """Retrieve any fact by ID, including deprecated ones."""
        raw = await self.engine.get_fact(fact_id)
        if not raw:
            return None
        return self._coerce_fact(raw)

    async def _fetch(self, query: str, params: list | tuple = ()) -> list[Fact]:
        """Lower-level fetch from engine database."""
        async with self.engine.session() as conn:
            cursor = await conn.execute(query, params)
            return [row_to_fact(r) for r in await cursor.fetchall()]  # type: ignore[reportArgumentType]

    async def get_all_active_facts(
        self,
        tenant_id: str = "default",
        project: str | None = None,
        fact_types: list[str] | None = None,
    ) -> list[Fact]:
        """Retrieve all active facts, delegated to QueryMixin and wrapped in models."""
        results = await self.engine.get_all_active_facts(
            tenant_id=tenant_id, project=project, fact_types=fact_types
        )
        return [self._coerce_fact(r) for r in results]

    async def recall(
        self, project: str, tenant_id: str = "default", limit: int | None = None, offset: int = 0
    ) -> list[Fact]:
        """Scored recall delegated to QueryMixin and wrapped in models."""
        results = await self.engine.recall(
            project=project, tenant_id=tenant_id, limit=limit, offset=offset
        )
        return [self._coerce_fact(r) for r in results]

    async def history(
        self, project: str, tenant_id: str = "default", as_of: str | None = None
    ) -> list[Fact]:
        """Temporal history delegated to QueryMixin."""
        results = await self.engine.history(project=project, tenant_id=tenant_id, as_of=as_of)
        return [self._coerce_fact(r) for r in results]

    async def time_travel(
        self, tx_id: int, tenant_id: str = "default", project: str | None = None
    ) -> list[Fact]:
        """Project state reconstruction delegated to QueryMixin."""
        results = await self.engine.time_travel(tx_id=tx_id, tenant_id=tenant_id)
        return [self._coerce_fact(r) for r in results]

    reconstruct_state = time_travel

    async def register_ghost(self, reference: str, context: str, project: str) -> str:
        """Register a new ghost, delegated to GhostMixin."""
        return await self.engine.register_ghost(reference, context, project)

    async def stats(self) -> dict:
        """System stats delegated to QueryMixin."""
        return await self.engine.stats()

    async def search(self, *args, **kwargs) -> list[Fact]:
        return await self.engine.search(*args, **kwargs)

    async def update(self, *args, **kwargs) -> Any:
        return await self.engine.update(*args, **kwargs)  # type: ignore[reportAttributeAccessIssue]

    async def deprecate(self, *args, **kwargs) -> Any:
        return await self.engine.deprecate(*args, **kwargs)

    async def graph(self, *args, **kwargs) -> Any:
        """Retrieve graph visualization data, delegated to QueryMixin."""
        import cortex.graph

        async with self.engine.session() as conn:
            return await cortex.graph.get_graph(conn, *args, **kwargs)

    async def query_entity(self, *args, **kwargs) -> Any:
        """Query detailed information about an entity, delegated to QueryMixin."""
        import cortex.graph

        async with self.engine.session() as conn:
            return await cortex.graph.query_entity(conn, *args, **kwargs)

    async def find_path(self, *args, **kwargs) -> Any:
        import cortex.graph

        async with self.engine.session() as conn:
            return await cortex.graph.find_path(conn, *args, **kwargs)

    async def get_context_subgraph(self, *args, **kwargs) -> Any:
        import cortex.graph

        async with self.engine.session() as conn:
            return await cortex.graph.get_context_subgraph(conn, *args, **kwargs)
