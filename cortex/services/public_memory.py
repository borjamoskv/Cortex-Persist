"""Shared public-memory service for HTTP and MCP entrypoints."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import TYPE_CHECKING, Any

from cortex import __version__
from cortex.types.models import FactResponse, SearchResult, StatusResponse, StoreResponse

if TYPE_CHECKING:
    from cortex.engine import CortexEngine as AsyncCortexEngine

__all__ = [
    "PublicMemoryService",
    "fact_like_to_dict",
    "to_fact_response",
    "to_search_result",
]


def fact_like_to_dict(fact: Any) -> dict[str, Any]:
    """Normalize engine fact records into a dict-backed public shape."""
    if isinstance(fact, dict):
        return fact

    to_dict = getattr(fact, "to_dict", None)
    if callable(to_dict):
        return to_dict()

    return {
        "id": getattr(fact, "id", None),
        "tenant_id": getattr(fact, "tenant_id", None),
        "project": getattr(fact, "project", ""),
        "content": getattr(fact, "content", ""),
        "fact_type": getattr(fact, "fact_type", "knowledge"),
        "tags": getattr(fact, "tags", []) or [],
        "confidence": getattr(fact, "confidence", "C3"),
        "valid_from": getattr(fact, "valid_from", None),
        "valid_until": getattr(fact, "valid_until", None),
        "source": getattr(fact, "source", None),
        "meta": getattr(fact, "meta", None),
        "created_at": getattr(fact, "created_at", None),
        "updated_at": getattr(fact, "updated_at", None),
        "tx_id": getattr(fact, "tx_id", None),
        "hash": getattr(fact, "hash", None),
        "consensus_score": getattr(fact, "consensus_score", None),
    }


def to_fact_response(fact: Any) -> FactResponse:
    """Map an internal fact-like object into the public API model."""
    data = fact_like_to_dict(fact)
    meta = data.get("meta")
    if meta is None:
        meta = data.get("metadata")

    return FactResponse(
        id=int(data["id"]),
        project=str(data.get("project", "")),
        content=str(data.get("content", "")),
        fact_type=str(data.get("fact_type", data.get("type", "knowledge"))),
        tags=list(data.get("tags") or []),
        confidence=data.get("confidence", "C3"),
        valid_from=data.get("valid_from"),
        valid_until=data.get("valid_until"),
        source=data.get("source"),
        meta=meta,
        created_at=str(data.get("created_at") or ""),
        updated_at=str(data.get("updated_at") or data.get("created_at") or ""),
        tx_id=data.get("tx_id"),
        hash=data.get("hash"),
        consensus_score=(
            float(data["consensus_score"]) if data.get("consensus_score") is not None else None
        ),
        is_tombstoned=bool(data.get("is_tombstoned", False)),
    )


def to_search_result(result: Any) -> SearchResult:
    """Map an internal search result into the public API model."""
    return SearchResult(
        fact_id=result.fact_id,
        project=result.project,
        content=result.content,
        fact_type=result.fact_type,
        score=result.score,
        tags=result.tags,
        created_at=result.created_at,
        updated_at=result.updated_at,
        meta=getattr(result, "meta", None),
        tx_id=getattr(result, "tx_id", None),
        hash=getattr(result, "hash", None),
        context=getattr(result, "graph_context", None) or getattr(result, "context", None),
    )


def _normalize_public_payload(value: Any) -> Any:
    """Convert service return values into JSON-safe public payloads."""
    if is_dataclass(value):
        return asdict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump()
    return value


class PublicMemoryService:
    """Canonical typed entrypoint for store/search/recall/status operations."""

    __slots__ = ("engine",)

    def __init__(self, engine: AsyncCortexEngine) -> None:
        self.engine = engine

    async def store(
        self,
        *,
        project: str,
        content: str,
        fact_type: str = "knowledge",
        tags: list[str] | None = None,
        source: str | None = None,
        meta: dict[str, Any] | None = None,
        parent_decision_id: int | None = None,
        tenant_id: str | None = None,
        confidence: str | None = None,
    ) -> StoreResponse:
        payload: dict[str, Any] = {
            "project": project,
            "content": content,
            "fact_type": fact_type,
            "tags": tags or [],
        }
        if source is not None:
            payload["source"] = source
        if meta is not None:
            payload["meta"] = meta
        if parent_decision_id is not None:
            payload["parent_decision_id"] = parent_decision_id
        if tenant_id is not None:
            payload["tenant_id"] = tenant_id
        if confidence is not None:
            payload["confidence"] = confidence

        fact_id = await self.engine.store(**payload)
        return StoreResponse(fact_id=fact_id, project=project, message="Fact stored")

    async def batch_store(
        self,
        facts: list[dict[str, Any]],
    ) -> list[int]:
        """Store multiple facts via the canonical engine contract."""
        return await self.engine.store_many(facts)

    async def recall_project(
        self,
        *,
        project: str,
        limit: int | None = None,
        offset: int = 0,
        include_deprecated: bool = False,
        tenant_id: str | None = None,
    ) -> list[FactResponse]:
        if include_deprecated:
            payload: dict[str, Any] = {"project": project}
            if tenant_id is not None:
                payload["tenant_id"] = tenant_id
            facts = await self.engine.history(**payload)
            if offset or limit is not None:
                end = None if limit is None else offset + limit
                facts = facts[offset:end]
        else:
            payload = {
                "project": project,
                "offset": offset,
            }
            if limit is not None:
                payload["limit"] = limit
            if tenant_id is not None:
                payload["tenant_id"] = tenant_id

            facts = await self.engine.recall(**payload)
            facts = [fact for fact in facts if fact_like_to_dict(fact).get("valid_until") is None]
        return [to_fact_response(fact) for fact in facts]

    async def list_active_facts(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        tenant_id: str | None = None,
    ) -> list[FactResponse]:
        payload: dict[str, Any] = {}
        if tenant_id is not None:
            payload["tenant_id"] = tenant_id

        facts = await self.engine.get_all_active_facts(**payload)
        return [to_fact_response(fact) for fact in facts[offset : offset + limit]]

    async def search(
        self,
        *,
        query: str,
        top_k: int = 5,
        project: str | None = None,
        tenant_id: str | None = None,
        as_of: str | None = None,
        fact_type: str | None = None,
        tags: list[str] | None = None,
        graph_depth: int = 0,
        include_graph: bool = False,
        preserve_null_filters: bool = False,
    ) -> list[SearchResult]:
        payload: dict[str, Any] = {
            "query": query,
            "top_k": top_k,
        }
        for key, value in (
            ("project", project),
            ("tenant_id", tenant_id),
            ("as_of", as_of),
            ("fact_type", fact_type),
            ("tags", tags),
        ):
            if preserve_null_filters or value is not None:
                payload[key] = value

        if preserve_null_filters or graph_depth != 0:
            payload["graph_depth"] = graph_depth
        if preserve_null_filters or include_graph:
            payload["include_graph"] = include_graph

        results = await self.engine.search(**payload)
        return [to_search_result(result) for result in results]

    async def get_fact(
        self,
        fact_id: int,
        *,
        tenant_id: str | None = None,
    ) -> FactResponse | None:
        payload: dict[str, Any] = {"fact_id": fact_id}
        if tenant_id is not None:
            payload["tenant_id"] = tenant_id

        fact = await self.engine.get_fact(**payload)
        if not fact:
            return None
        return to_fact_response(fact)

    async def get_fact_record(
        self,
        fact_id: int,
        *,
        tenant_id: str | None = None,
    ) -> dict[str, Any] | None:
        payload: dict[str, Any] = {"fact_id": fact_id}
        if tenant_id is not None:
            payload["tenant_id"] = tenant_id

        fact = await self.engine.get_fact(**payload)
        if not fact:
            return None
        return fact_like_to_dict(fact)

    async def deprecate(
        self,
        fact_id: int,
        *,
        reason: str,
    ) -> bool:
        return await self.engine.deprecate(fact_id, reason=reason)

    async def verify_ledger(self) -> dict[str, Any]:
        report = await self.engine.verify_ledger()
        return {
            "valid": report["valid"],
            "violations": len(report.get("violations", [])),
            "transactions_checked": report.get("tx_checked", report.get("tx_count", 0)),
            "roots_checked": report.get("roots_checked", 0),
        }

    async def causal_chain(
        self,
        *,
        fact_id: int,
        direction: str = "down",
        max_depth: int = 10,
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "fact_id": fact_id,
            "direction": direction,
            "max_depth": max_depth,
        }
        if tenant_id is not None:
            payload["tenant_id"] = tenant_id

        chain = await self.engine.get_causal_chain(**payload)
        return [fact_like_to_dict(fact) for fact in chain]

    async def fact_history(
        self,
        fact_id: int,
        *,
        tenant_id: str | None = None,
        max_depth: int = 50,
    ) -> list[FactResponse]:
        chain = await self.causal_chain(
            fact_id=fact_id,
            direction="up",
            max_depth=max_depth,
            tenant_id=tenant_id,
        )
        return [to_fact_response(fact) for fact in chain]

    async def status(self) -> StatusResponse:
        stats = await self.engine.stats()
        return StatusResponse(
            version=__version__,
            total_facts=stats["total_facts"],
            active_facts=stats["active_facts"],
            deprecated=stats["deprecated_facts"],
            projects=stats["project_count"],
            embeddings=stats["embeddings"],
            transactions=stats["transactions"],
            db_size_mb=stats["db_size_mb"],
        )

    async def continual_learning_status(
        self,
        *,
        tenant_id: str,
        domain: str | None = None,
    ) -> dict[str, Any]:
        """Expose tenant-scoped continual-learning status when the sidecar exists."""
        manager = getattr(self.engine, "memory", None)
        if manager is None or not hasattr(manager, "continual_learning_status"):
            return {
                "enabled": False,
                "tenant_id": tenant_id,
                "domain": domain.strip() if isinstance(domain, str) else None,
            }
        return await manager.continual_learning_status(tenant_id=tenant_id, domain=domain)

    async def plan_continual_update(
        self,
        *,
        tenant_id: str,
        domain: str,
        policy_violation: bool = False,
    ) -> dict[str, Any] | None:
        """Return a public continual-learning micro-update plan if enabled."""
        manager = getattr(self.engine, "memory", None)
        if manager is None or not hasattr(manager, "plan_continual_update"):
            return None
        plan = await manager.plan_continual_update(
            tenant_id=tenant_id,
            domain=domain,
            policy_violation=policy_violation,
        )
        if plan is None:
            return None
        return _normalize_public_payload(plan)

    async def execute_continual_update(
        self,
        *,
        tenant_id: str,
        domain: str,
        policy_violation: bool = False,
        critical_domains: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Execute a continual-learning micro-update through the configured backend."""
        manager = getattr(self.engine, "memory", None)
        if manager is None or not hasattr(manager, "execute_continual_update"):
            return None
        execution = await manager.execute_continual_update(
            tenant_id=tenant_id,
            domain=domain,
            policy_violation=policy_violation,
            critical_domains=critical_domains or [],
        )
        if execution is None:
            return None
        return _normalize_public_payload(execution)

    async def forget_continual_memory(
        self,
        *,
        tenant_id: str,
        user_id: str,
        query: str,
    ) -> dict[str, Any] | None:
        """Request selective forgetting through the continual-learning sidecar."""
        manager = getattr(self.engine, "memory", None)
        if manager is None or not hasattr(manager, "forget_continual_memory"):
            return None
        result = await manager.forget_continual_memory(
            tenant_id=tenant_id,
            user_id=user_id,
            query=query,
        )
        if result is None:
            return None
        normalized = _normalize_public_payload(result)
        if not isinstance(normalized, dict):
            raise TypeError("forget_continual_memory must return a mapping-compatible payload")
        return normalized
