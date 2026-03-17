"""
CORTEX v5.0 — Python SDK Client

This module implements the SORTU-Ω v0.2 public SDK surface.
It exposes a main `CortexClient`, which branches into modular domain
clients: memory, trace, verification, coordination, and runtime.

Usage:
    from cortex_persist.client import CortexClient

    client = CortexClient(api_key="ctx_...")
    
    # Store a memory
    client.memory.store("my-project", "The system must not use floats for money")
    
    # Query with trust semantics
    result = client.memory.query("How should money be stored?")
    print(f"Confidence: {result.evidence.grade}")
"""

import os
from collections.abc import Callable
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

__all__ = ["CortexClient"]


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
                mitigation=response_data.get("mitigation")
            )
        elif category in ["dependency", "storage", "runtime", "capability"]:
            return FailureError(
                status_code=status_code,
                detail=detail,
                code=code,
                category=category,
                is_retryable=response_data.get("is_retryable", False),
                retry_after_ms=response_data.get("retry_after_ms")
            )
            
    # Fallback for generic errors
    return CortexError(status_code, detail, code)


class BaseClientDomain:
    """Base class for domain-specific clients, providing request execution."""

    def __init__(self, request_fn: Callable[..., Any]):
        self._request = request_fn


# ─── 1. Memory Domain ──────────────────────────────────────────────────

class MemoryClient(BaseClientDomain):
    """Canonical API for Working Memory Integration."""

    def query(self, input_data: QueryInput) -> QueryResult:
        """Execute a trust-aware memory query."""
        payload = {k: v for k, v in input_data.items() if v is not None}
        if "strategy" not in payload:
            payload["strategy"] = "auto"
        if "tenant_id" not in payload:
            payload["tenant_id"] = "default"

        data = self._request("POST", "/v1/memory/query", json=payload)

        # Parse deeply nested QueryResult
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
            verification_proof=data["evidence"].get("verification_proof")
        )
        
        plan = QueryPlan(
            routing_strategy=data["plan"]["routing_strategy"],
            execution_time_ms=data["plan"]["execution_time_ms"],
            degraded=data["plan"]["degraded"],
            warnings=data["plan"].get("warnings", [])
        )

        return QueryResult(items=items, evidence=evidence, plan=plan)

    def store(
        self,
        project: str,
        content: str,
        fact_type: str = "knowledge",
        tags: list[str] | None = None,
        source_uri: str = "cortex:sdk",
        metadata: dict[str, Any] | None = None,
        tenant_id: str = "default",
    ) -> AcceptanceResult:
        """Store a new piece of evidence."""
        payload = {
            "project": project,
            "content": content,
            "fact_type": fact_type,
            "tags": tags or [],
            "source_uri": source_uri,
            "metadata": metadata or {},
            "tenant_id": tenant_id,
        }
        
        data = self._request("POST", "/v1/memory/facts", json=payload)
        return AcceptanceResult(
            accepted=True,
            operation_id=data["id"],
            warnings=data.get("warnings", [])
        )

    def delete(self, fact_id: str, tenant_id: str = "default") -> AcceptanceResult:
        """Tombstone a fact."""
        data = self._request("DELETE", f"/v1/memory/facts/{fact_id}", params={"tenant_id": tenant_id})
        return AcceptanceResult(
            accepted=True,
            operation_id=fact_id,
            warnings=[]
        )


# ─── 2. Trace Domain ───────────────────────────────────────────────────

class TraceClient(BaseClientDomain):
    """Canonical API for Audit & Trace Integration."""

    def get_causal_chain(self, fact_id: str, tenant_id: str = "default") -> list[dict[str, Any]]:
        """Retrieve the upstream dependencies that produced a fact."""
        return self._request(
            "GET", 
            f"/v1/trace/chain/{fact_id}", 
            params={"tenant_id": tenant_id}
        )

    def get_ledger_proof(self, fact_id: str, tenant_id: str = "default") -> dict[str, Any]:
        """Retrieve cryptographic proof of existence for a fact."""
        return self._request(
            "GET", 
            f"/v1/trace/proof/{fact_id}", 
            params={"tenant_id": tenant_id}
        )


# ─── 3. Verification Domain ────────────────────────────────────────────

class VerificationClient(BaseClientDomain):
    """Canonical API for Integrity Verification."""

    def verify_integrity(self, fact_id: str, tenant_id: str = "default") -> IntegrityState:
        """Force a cryptographic and referential integrity check."""
        data = self._request(
            "POST", 
            f"/v1/verify/integrity/{fact_id}", 
            params={"tenant_id": tenant_id}
        )
        return IntegrityState(data["status"])

    def audit_taint(self, target_id: str, tenant_id: str = "default") -> TaintState:
        """Calculate the inherited taint from corrupted upstream dependencies."""
        data = self._request(
            "GET", 
            f"/v1/verify/taint/{target_id}", 
            params={"tenant_id": tenant_id}
        )
        return TaintState(data["state"])


# ─── 4. Coordination Domain ────────────────────────────────────────────

class CoordinationClient(BaseClientDomain):
    """Canonical API for Swarm Coordination."""

    def register_agent(
        self, 
        agent_id: str, 
        capabilities: list[str], 
        tenant_id: str = "default"
    ) -> AcceptanceResult:
        """Announce presence to the coordination tier."""
        payload = {
            "agent_id": agent_id,
            "capabilities": capabilities,
            "tenant_id": tenant_id,
        }
        data = self._request("POST", "/v1/coordination/agents", json=payload)
        return AcceptanceResult(
            accepted=True,
            operation_id=data["session_id"],
            warnings=[]
        )

    def emit_event(
        self, 
        event_type: str, 
        payload: dict[str, Any], 
        causality_id: str | None = None,
        tenant_id: str = "default"
    ) -> AcceptanceResult:
        """Publish a localized, fire-and-forget, non-ordered event."""
        data = {
            "event_type": event_type,
            "payload": payload,
            "tenant_id": tenant_id,
        }
        if causality_id:
            data["causality_id"] = causality_id
            
        res = self._request("POST", "/v1/coordination/events", json=data)
        return AcceptanceResult(
            accepted=True,
            operation_id=res["event_id"],
            warnings=[]
        )


# ─── 5. Runtime Domain ─────────────────────────────────────────────────

class RuntimeClient(BaseClientDomain):
    """Canonical API for Engine Lifecycle and Health."""

    def health(self) -> HealthReport:
        """Get authoritative system health, ignoring cached states."""
        data = self._request("GET", "/v1/runtime/health")
        
        return HealthReport(
            status=data["status"],
            components=data.get("components", {}),
            degraded_features=data.get("degraded_features", []),
            warnings=data.get("warnings", [])
        )


# ─── Main Client ───────────────────────────────────────────────────────

class CortexClient:
    """
    SORTU-Ω Canonical Persistent Trust SDK.
    
    Provides access to the five core domains defined in SDK-SURFACE.md:
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
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers=self._headers(),
        )

        # Mount domains
        self.memory = MemoryClient(self._request)
        self.trace = TraceClient(self._request)
        self.verify = VerificationClient(self._request)
        self.coordination = CoordinationClient(self._request)
        self.runtime = RuntimeClient(self._request)

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _request(self, method: str, path: str, **kwargs) -> Any:
        try:
            resp = self._client.request(method, path, **kwargs)
        except httpx.RequestError as exc:
            raise FailureError(
                status_code=503,
                detail=f"Network error connecting to {self.base_url}: {str(exc)}",
                code="ERR_FAIL_DEP_000",
                category="dependency",
                is_retryable=True
            ) from exc

        if resp.status_code >= 400:
            try:
                err_data = resp.json()
            except ValueError:
                err_data = {"detail": resp.text, "code": "ERR_FAIL_UNKNOWN"}
            
            raise _parse_error_response(resp.status_code, err_data)

        # Successful responses always return JSON per contract
        return resp.json()

    def close(self):
        """Close the underlying HTTP client session."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
