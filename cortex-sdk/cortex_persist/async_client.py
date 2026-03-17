"""
CORTEX v5.0 — Async Python SDK Client

This module implements the SORTU-Ω v0.2 public SDK surface asynchronously.
It exposes a main `AsyncCortexClient`, which branches into modular domain
clients: memory, trace, verification, coordination, and runtime.

Usage:
    from cortex_persist.async_client import AsyncCortexClient

    async with AsyncCortexClient(api_key="ctx_...") as client:
        # Store a memory
        await client.memory.store("my-project", "The system must not use floats for money")

        # Query with trust semantics
        result = await client.memory.query("How should money be stored?")
        print(f"Confidence: {result.evidence.grade}")
"""

import os
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

import httpx

from .exceptions import CortexError, FailureError, RejectionError
from .models import (
    AcceptanceResult,
    EvidenceItem,
    EvidenceLevel,
    HealthReport,
    IntegrityState,
    QueryEvidenceLevel,
    QueryInput,
    QueryPlan,
    QueryResult,
    TaintState,
    TrustGrade,
)

T = TypeVar("T")

__all__ = ["AsyncCortexClient"]


def _parse_error_response(status_code: int, response_data: dict[str, Any]) -> CortexError:
    """Parses an error response into either a RejectionError or FailureError."""
    detail = response_data.get("detail", "Unknown error")
    code = response_data.get("code", "UNKNOWN_ERROR")

    if "category" in response_data:
        category = response_data["category"]
        if category in ["policy", "safety", "consistency", "integrity", "compliance"]:
            return RejectionError(
                status_code=status_code,
                detail=detail,
                code=code,
                category=category,
                severity=response_data.get("severity", "medium"),
                layer=response_data.get("layer", "admission"),
                mitigation=response_data.get("mitigation"),
            )
        elif category in ["dependency", "storage", "runtime", "capability"]:
            return FailureError(
                status_code=status_code,
                detail=detail,
                code=code,
                category=category,
                is_retryable=response_data.get("is_retryable", False),
                retry_after_ms=response_data.get("retry_after_ms"),
            )

    # Fallback for generic errors
    return CortexError(status_code, detail, code)


class BaseAsyncClientDomain:
    """Base class for async domain-specific clients."""

    def __init__(self, request_fn: Callable[..., Coroutine[Any, Any, Any]]):
        self._request = request_fn


# ─── 1. Memory Domain ──────────────────────────────────────────────────


class AsyncMemoryClient(BaseAsyncClientDomain):
    """Canonical Async API for Working Memory Integration."""

    async def query(self, input_data: QueryInput) -> QueryResult:
        """Execute a trust-aware memory query asynchronously."""
        payload = {k: v for k, v in input_data.items() if v is not None}
        if "strategy" not in payload:
            payload["strategy"] = "auto"
        if "tenant_id" not in payload:
            payload["tenant_id"] = "default"

        data = await self._request("POST", "/v1/memory/query", json=payload)

        items = [
            EvidenceItem(
                id=i["id"],
                project=i["project"],
                content=i["content"],
                fact_type=i["fact_type"],
                tags=i.get("tags", []),
                created_at=i["created_at"],
                valid_from=i["valid_from"],
                valid_until=i.get("valid_until"),
                source_uri=i["source_uri"],
                confidence=i["confidence"],
                evidence_level=EvidenceLevel(i["evidence_level"]),
                integrity=IntegrityState(i["integrity"]),
                taint=TaintState(i["taint"]),
                is_tombstoned=i.get("is_tombstoned", False),
                metadata=i.get("metadata", {}),
            )
            for i in data["items"]
        ]

        evidence = QueryEvidenceLevel(
            level=EvidenceLevel(data["evidence"]["level"]),
            grade=TrustGrade(data["evidence"]["grade"]),
            verification_proof=data["evidence"].get("verification_proof"),
        )

        plan = QueryPlan(
            routing_strategy=data["plan"]["routing_strategy"],
            execution_time_ms=data["plan"]["execution_time_ms"],
            degraded=data["plan"]["degraded"],
            warnings=data["plan"].get("warnings", []),
        )

        return QueryResult(items=items, evidence=evidence, plan=plan)

    async def store(
        self,
        project: str,
        content: str,
        fact_type: str = "knowledge",
        tags: list[str] | None = None,
        source_uri: str = "cortex:sdk",
        metadata: dict[str, Any] | None = None,
        tenant_id: str = "default",
    ) -> AcceptanceResult:
        """Store a new piece of evidence asynchronously."""
        payload = {
            "project": project,
            "content": content,
            "fact_type": fact_type,
            "tags": tags or [],
            "source_uri": source_uri,
            "metadata": metadata or {},
            "tenant_id": tenant_id,
        }

        data = await self._request("POST", "/v1/memory/facts", json=payload)
        return AcceptanceResult(
            accepted=True, operation_id=data["id"], warnings=data.get("warnings", [])
        )

    async def delete(self, fact_id: str, tenant_id: str = "default") -> AcceptanceResult:
        """Tombstone a fact asynchronously."""
        data = await self._request(
            "DELETE", f"/v1/memory/facts/{fact_id}", params={"tenant_id": tenant_id}
        )
        return AcceptanceResult(accepted=True, operation_id=fact_id, warnings=[])


# ─── 2. Trace Domain ───────────────────────────────────────────────────


class AsyncTraceClient(BaseAsyncClientDomain):
    """Canonical Async API for Audit & Trace Integration."""

    async def get_causal_chain(
        self, fact_id: str, tenant_id: str = "default"
    ) -> list[dict[str, Any]]:
        """Retrieve the upstream dependencies that produced a fact asynchronously."""
        return await self._request(
            "GET", f"/v1/trace/chain/{fact_id}", params={"tenant_id": tenant_id}
        )

    async def get_ledger_proof(self, fact_id: str, tenant_id: str = "default") -> dict[str, Any]:
        """Retrieve cryptographic proof of existence for a fact asynchronously."""
        return await self._request(
            "GET", f"/v1/trace/proof/{fact_id}", params={"tenant_id": tenant_id}
        )


# ─── 3. Verification Domain ────────────────────────────────────────────


class AsyncVerificationClient(BaseAsyncClientDomain):
    """Canonical Async API for Integrity Verification."""

    async def verify_integrity(self, fact_id: str, tenant_id: str = "default") -> IntegrityState:
        """Force a cryptographic and referential integrity check asynchronously."""
        data = await self._request(
            "POST", f"/v1/verify/integrity/{fact_id}", params={"tenant_id": tenant_id}
        )
        return IntegrityState(data["status"])

    async def audit_taint(self, target_id: str, tenant_id: str = "default") -> TaintState:
        """Calculate the inherited taint from corrupted upstream dependencies asynchronously."""
        data = await self._request(
            "GET", f"/v1/verify/taint/{target_id}", params={"tenant_id": tenant_id}
        )
        return TaintState(data["state"])


# ─── 4. Coordination Domain ────────────────────────────────────────────


class AsyncCoordinationClient(BaseAsyncClientDomain):
    """Canonical Async API for Swarm Coordination."""

    async def register_agent(
        self, agent_id: str, capabilities: list[str], tenant_id: str = "default"
    ) -> AcceptanceResult:
        """Announce presence to the coordination tier asynchronously."""
        payload = {
            "agent_id": agent_id,
            "capabilities": capabilities,
            "tenant_id": tenant_id,
        }
        data = await self._request("POST", "/v1/coordination/agents", json=payload)
        return AcceptanceResult(accepted=True, operation_id=data["session_id"], warnings=[])

    async def emit_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        causality_id: str | None = None,
        tenant_id: str = "default",
    ) -> AcceptanceResult:
        """Publish a localized, fire-and-forget, non-ordered event asynchronously."""
        data = {
            "event_type": event_type,
            "payload": payload,
            "tenant_id": tenant_id,
        }
        if causality_id:
            data["causality_id"] = causality_id

        res = await self._request("POST", "/v1/coordination/events", json=data)
        return AcceptanceResult(accepted=True, operation_id=res["event_id"], warnings=[])


# ─── 5. Runtime Domain ─────────────────────────────────────────────────


class AsyncRuntimeClient(BaseAsyncClientDomain):
    """Canonical Async API for Engine Lifecycle and Health."""

    async def health(self) -> HealthReport:
        """Get authoritative system health asynchronously."""
        data = await self._request("GET", "/v1/runtime/health")

        return HealthReport(
            status=data["status"],
            components=data.get("components", {}),
            degraded_features=data.get("degraded_features", []),
            warnings=data.get("warnings", []),
        )


# ─── Main Async Client ─────────────────────────────────────────────────


class AsyncCortexClient:
    """
    SORTU-Ω Canonical Persistent Trust Async SDK.

    Provides async access to the five core domains defined in SDK-SURFACE.md:
    .memory       - Working Memory
    .trace        - Audit & Forensics
    .verify       - Cryptographic Integrity
    .coordination - Swarm Bus
    .runtime      - Health & State
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8484",
        api_key: str | None = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("CORTEX_API_KEY", "")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers=self._headers(),
        )

        # Mount domains
        self.memory = AsyncMemoryClient(self._request)
        self.trace = AsyncTraceClient(self._request)
        self.verify = AsyncVerificationClient(self._request)
        self.coordination = AsyncCoordinationClient(self._request)
        self.runtime = AsyncRuntimeClient(self._request)

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        try:
            resp = await self._client.request(method, path, **kwargs)
        except httpx.RequestError as exc:
            raise FailureError(
                status_code=503,
                detail=f"Network error connecting to {self.base_url}: {str(exc)}",
                code="ERR_FAIL_DEP_000",
                category="dependency",
                is_retryable=True,
            ) from exc

        if resp.status_code >= 400:
            try:
                err_data = resp.json()
            except ValueError:
                err_data = {"detail": resp.text, "code": "ERR_FAIL_UNKNOWN"}

            raise _parse_error_response(resp.status_code, err_data)

        return resp.json()

    async def close(self):
        """Close the underlying HTTP client session."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
