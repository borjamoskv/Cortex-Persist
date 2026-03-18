from __future__ import annotations

import dataclasses
import logging
from typing import TYPE_CHECKING, Any, cast

from pydantic import ValidationError

from cortex.engine.models import Fact, row_to_fact
from cortex.engine.store_validators import validate_content
from cortex.immune.haiku import HaikuGuard
from cortex.utils.canonical import now_iso

if TYPE_CHECKING:
    from cortex.extensions.interfaces.engine import EngineProtocol

_FACT_FIELDS = {f.name for f in dataclasses.fields(Fact)}

__all__ = ["FactManager"]

logger = logging.getLogger("cortex.facts")


class FactManager:
    """Manages the full lifecycle and retrieval of facts."""

    def __init__(self, engine: EngineProtocol):
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
        tenant_id = self.engine._resolve_tenant(tenant_id)
        conn = conn or await self.engine.get_conn()

        # Ω₄: Aesthetic Integrity (Inmunidad Haiku)
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

            # V8 Semantic Deduplication
            if hasattr(self.engine, "embeddings") and self.engine.embeddings:
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
        except (OSError, RuntimeError, ValueError) as e:
            # The ValidationError import was moved to the top of the file.
            if isinstance(e, ValidationError):
                raise ValueError(f"Ingestion Validation Failed: {e}") from e
            logger.warning("V8 Ingestion check failed: %s", e)

        from cortex.engine.store_mixin import StoreMixin

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
            meta,
            valid_from,
            commit,
            tx_id,
        )

    async def store_many(self, facts: list[dict]) -> list[int]:
        if not facts:
            raise ValueError("Facts list cannot be empty")
        return await self.engine.store_many(facts)

    async def get_fact(self, fact_id: int) -> Fact | None:
        """Retrieve any fact by ID, including deprecated ones."""
        raw = await self.engine.get_fact(fact_id)
        if not raw:
            return None
        # Convert dict to Fact model
        return Fact(**raw)

    async def _fetch(self, query: str, params: list | tuple = ()) -> list[Fact]:
        """Lower-level fetch from engine database."""
        conn = await self.engine.get_conn()
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
        return [Fact(**{k: v for k, v in r.items() if k in _FACT_FIELDS}) for r in results]

    async def recall(
        self, project: str, tenant_id: str = "default", limit: int | None = None, offset: int = 0
    ) -> list[Fact]:
        """Scored recall delegated to QueryMixin and wrapped in models."""
        results = await self.engine.recall(
            project=project, tenant_id=tenant_id, limit=limit, offset=offset
        )
        return [Fact(**{k: v for k, v in r.items() if k in _FACT_FIELDS}) for r in results]

    async def history(
        self, project: str, tenant_id: str = "default", as_of: str | None = None
    ) -> list[Fact]:
        """Temporal history delegated to QueryMixin."""
        results = await self.engine.history(project=project, tenant_id=tenant_id, as_of=as_of)
        return [Fact(**{k: v for k, v in r.items() if k != "type"}) for r in results]

    async def time_travel(
        self, tx_id: int, tenant_id: str = "default", project: str | None = None
    ) -> list[Fact]:
        """Project state reconstruction delegated to QueryMixin."""
        results = await self.engine.time_travel(tx_id=tx_id, tenant_id=tenant_id)
        return [Fact(**{k: v for k, v in r.items() if k != "type"}) for r in results]

    reconstruct_state = time_travel

    async def register_ghost(self, reference: str, context: str, project: str) -> str:
        """Register a new ghost, delegated to GhostMixin."""
        return await self.engine.register_ghost(reference, context, project)

    async def stats(self) -> dict:
        """System stats delegated to QueryMixin."""
        return await self.engine.stats()

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
