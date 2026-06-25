"""CORTEX - Causal Evidence Fundamentals.

Deterministic, hash-verifiable structural components.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _canonical_dt(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_value(value: Any) -> Any:
    from enum import Enum

    if isinstance(value, Enum):
        return _normalize_value(value.value)
    if isinstance(value, dict):
        return {str(k): _normalize_value(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [_normalize_value(v) for v in value]
    if isinstance(value, datetime):
        return _canonical_dt(value)
    if hasattr(value, "__dict__") and not isinstance(value, type):
        return _normalize_value(vars(value))
    return value


def _canonical_json(payload: Any) -> str:
    return json.dumps(_normalize_value(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True, slots=True)
class Source:
    """Immutable, verifiable data source."""
    uri: str
    content_hash: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def canonical(self) -> dict[str, Any]:
        return {
            "uri": self.uri,
            "content_hash": self.content_hash,
            "metadata": _normalize_value(dict(self.metadata)),
        }


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    """Atomic causal wrapper around retrieved or generated evidence."""
    query: str
    sources: tuple[Source, ...]
    retrieved_at: datetime
    evidence_hash: str

    @classmethod
    def forge(cls, query: str, sources: list[Source], retrieved_at: datetime) -> EvidenceBundle:
        payload = {
            "query": query,
            "sources": [s.canonical() for s in sources],
            "retrieved_at": _canonical_dt(retrieved_at),
        }
        encoded = _canonical_json(payload).encode("utf-8")
        evidence_hash = hashlib.sha3_256(encoded).hexdigest()

        return cls(
            query=query,
            sources=tuple(sources),
            retrieved_at=retrieved_at,
            evidence_hash=evidence_hash,
        )

    def canonical(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "sources": [s.canonical() for s in self.sources],
            "retrieved_at": _canonical_dt(self.retrieved_at),
            "evidence_hash": self.evidence_hash,
        }


@dataclass(frozen=True, slots=True)
class ClosurePayload:
    """Canonical sealed payload consumed by the guard."""
    schema_version: str
    proof_kind: str
    claims: tuple[dict[str, Any], ...]
    evidence: EvidenceBundle
    verdict: bool
    payload_hash: str
    info_exergy: float = 1.0
    snark_proof: dict[str, Any] | None = None
    ancestor_hash: str | None = None

    @classmethod
    def seal(
        cls,
        claims: list[dict[str, Any]],
        evidence: EvidenceBundle,
        verdict: bool,
        *,
        schema_version: str = "v1",
        proof_kind: str = "sealed-claim-set",
        info_exergy: float | None = None,
        snark_proof: dict[str, Any] | None = None,
        ancestor_hash: str | None = None,
    ) -> ClosurePayload:
        normalized_claims = tuple(_normalize_value(c) for c in claims)
        
        # [C5-REAL] Dynamic Thermodynamic Calculation (E-INFO-01)
        if info_exergy is None:
            try:
                from legacy_research.shannon.entropy import compute_fact_entropy
                evidence_text = _canonical_json(evidence.canonical())
                h = compute_fact_entropy(evidence_text)
                if h <= 0:
                    h = 1.0  # Fallback to prevent ZeroDivisionError
                c_v = len(normalized_claims)
                info_exergy = round(c_v / h, 6)
            except ImportError:
                info_exergy = 1.0

        payload = {
            "schema_version": schema_version,
            "proof_kind": proof_kind,
            "claims": list(normalized_claims),
            "evidence_hash": evidence.evidence_hash,
            "verdict": verdict,
        }
        encoded = _canonical_json(payload).encode("utf-8")
        payload_hash = hashlib.sha3_256(encoded).hexdigest()

        return cls(
            schema_version=schema_version,
            proof_kind=proof_kind,
            claims=normalized_claims,
            evidence=evidence,
            verdict=verdict,
            payload_hash=payload_hash,
            info_exergy=info_exergy,
            snark_proof=snark_proof,
            ancestor_hash=ancestor_hash,
        )

    def canonical(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "proof_kind": self.proof_kind,
            "claims": list(self.claims),
            "evidence_hash": self.evidence.evidence_hash,
            "verdict": self.verdict,
            "info_exergy": self.info_exergy,
        }
        return {
            **payload,
            "payload_hash": self.payload_hash,
        }
