# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import logging
import sqlite3
from typing import TYPE_CHECKING, Any

from cortex.engine.mixins.base import EngineMixinBase

if TYPE_CHECKING:
    from cortex.search.causal_gap import CausalGap


__all__ = ["SearchMixin"]

logger = logging.getLogger("cortex.engine.search")


class SearchMixin(EngineMixinBase):
    """Mixin for semantic, text, and graph-augmented search operations."""

    async def search(
        self,
        query: str,
        tenant_id: str = "default",
        top_k: int = 5,
        project: str | None = None,
        as_of: str | None = None,
        graph_depth: int = 0,
        include_graph: bool = False,
        confidence: str | None = None,
        causal_gap: CausalGap | None = None,
        **kwargs,
    ) -> list[Any]:
        """Perform hybrid search (Vector + Text) with optional Graph-RAG context."""
        import json
        from dataclasses import asdict

        from cortex.cache import RedisL1Cache
        from cortex.search import hybrid_search, text_search
        from cortex.search.models import SearchResult

        tenant_id = self._resolve_tenant(tenant_id)
        cache = RedisL1Cache.singleton()
        cache_key = None

        if cache.available:
            try:
                # Deterministic representation of search arguments
                args_hash = cache.cache_key_hash(
                    project or "",
                    query,
                    str(top_k),
                    str(as_of or ""),
                    str(graph_depth),
                    str(include_graph),
                    str(confidence or ""),
                    json.dumps(kwargs, sort_keys=True),
                )
                cache_key = f"search:{tenant_id}:{args_hash}"
                cached = cache.get(cache_key)
                if cached is not None:
                    data = json.loads(cached.decode("utf-8"))
                    results = [SearchResult(**item) for item in data]
                    logger.debug("[L1 Cache] Hit for tenant=%s, query='%s'", tenant_id, query[:30])
                    return results
            except Exception as e:
                logger.warning("[L1 Cache] Lookup failed: %s", e)

        async with self.session() as conn:
            try:
                # 1. Perform Hybrid Search
                embedder = self._get_embedder()
                embedding = embedder.embed(query)

                results = await hybrid_search(
                    conn=conn,
                    query=query,
                    query_embedding=embedding,
                    top_k=top_k,
                    tenant_id=tenant_id,
                    project=project,
                    as_of=as_of,
                    confidence=confidence,
                    causal_gap=causal_gap,
                    **kwargs,
                )

                if not results:
                    # Fallback to pure text search if hybrid yields nothing
                    results = await text_search(
                        conn,
                        query,
                        tenant_id=tenant_id,
                        project=project,
                        limit=top_k,
                        as_of=as_of,
                        confidence=confidence,
                        **kwargs,
                    )

                # 2. Enrich with Graph Context if requested
                if results and (graph_depth > 0 or include_graph):
                    await SearchMixin._enrich_with_graph_context(
                        self, conn, results, query, graph_depth, tenant_id=tenant_id
                    )

                # 3. [CORTEX v10] Read-Path Epistemic Membrane (Taint Propagation)
                for r in results:
                    meta = getattr(r, "meta", {}) or {}
                    confidence = getattr(r, "confidence", meta.get("confidence", "UNKNOWN"))
                    is_c5 = confidence in ("C5", "C5-REAL", "C5-Static", "C5-Dynamic")
                    has_taint = "cortex_taint" in meta

                    if not is_c5 and not has_taint:
                        # Append the deterministic tag to avoid Knowledge Laundering
                        original_content = getattr(r, "content", "")
                        r.content = f"[EPISTEMIC_WARNING: PROBABILISTIC_ORIGIN]\n{original_content}"

                # Cache the results
                if cache.available and cache_key is not None:
                    try:
                        serialized = json.dumps([asdict(r) for r in results]).encode("utf-8")
                        cache.set(cache_key, serialized)
                    except Exception as e:
                        logger.warning("[L1 Cache] Set failed: %s", e)

                return results

            except (sqlite3.Error, OSError, RuntimeError) as e:
                logger.exception("Hybrid Graph-RAG search failed: %s", e)
                # Ultimate fallback to basic text search
                fallback_results = await text_search(
                    conn,
                    query,
                    tenant_id=tenant_id,
                    project=project,
                    limit=top_k,
                    as_of=as_of,
                    confidence=confidence,
                    **kwargs,
                )

                # 3. [CORTEX v10] Read-Path Epistemic Membrane (Taint Propagation) - Fallback
                for r in fallback_results:
                    meta = getattr(r, "meta", {}) or {}
                    conf = getattr(r, "confidence", meta.get("confidence", "UNKNOWN"))
                    is_c5 = conf in ("C5", "C5-REAL", "C5-Static", "C5-Dynamic")
                    has_taint = "cortex_taint" in meta

                    if not is_c5 and not has_taint:
                        original_content = getattr(r, "content", "")
                        r.content = f"[EPISTEMIC_WARNING: PROBABILISTIC_ORIGIN]\n{original_content}"

                # Cache the fallback results
                if cache.available and cache_key is not None:
                    try:
                        serialized = json.dumps([asdict(r) for r in fallback_results]).encode(
                            "utf-8"
                        )
                        cache.set(cache_key, serialized)
                    except Exception as e:
                        logger.warning("[L1 Cache] Set failed: %s", e)

                return fallback_results

    async def _enrich_with_graph_context(
        self, conn, results: list[Any], query: str, graph_depth: int, tenant_id: str = "default"
    ) -> None:
        """Helper to enrich search results with graph context."""
        try:
            from cortex.graph import extract_entities, get_context_subgraph
        except Exception as exc:
            logger.debug("Graph context enrichment unavailable: %s", exc)
            return

        entities = extract_entities(query)
        seeds = [e["name"] for e in entities]

        if not seeds and results:
            top_content = " ".join([r.content for r in results[:2]])
            top_entities = extract_entities(top_content)
            seeds = [e["name"] for e in top_entities]

        if seeds:
            subgraph = await get_context_subgraph(
                conn, seeds, depth=graph_depth or 1, max_nodes=50, tenant_id=tenant_id
            )

            if results and (subgraph.get("nodes") or subgraph.get("edges")):
                results[0].graph_context = {"graph": subgraph, "seeds": seeds}

    def record_bm25_feedback(
        self, engine_used: str, response_digest: str, tenant_id: str = "default"
    ) -> None:
        """Inject (engine_used, response_digest) into BM25 feedback loop as a fire-and-forget async task."""
        import asyncio

        async def _inject_feedback():
            try:
                # Inyectar logica de retroalimentacion BM25 (ej. tabla FTS o tabla de tracking)
                async with self.session() as conn:
                    # Ejemplo asumiendo esquema FTS5 genérico en cortex.db
                    await conn.execute(
                        "INSERT INTO llm_telemetry (engine_used, response_digest, tenant_id) VALUES (?, ?, ?)",
                        (engine_used, response_digest, tenant_id)
                    )
                    await conn.commit()
                logger.debug("BM25 feedback injected: %s", engine_used)
            except Exception as e:
                logger.error("Failed to inject BM25 feedback: %s", e)

        # Disparar tarea fire-and-forget sin bloquear el event loop principal
        asyncio.create_task(_inject_feedback())
