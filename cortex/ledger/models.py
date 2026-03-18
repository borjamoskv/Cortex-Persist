from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Optional

SemanticStatus = Literal["pending", "processing", "indexed", "failed"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class IntentPayload:
    goal: str
    task_id: Optional[str] = None
    macro_objective: Optional[str] = None
    rationale: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ActionTarget:
    app: Optional[str] = None
    role: Optional[str] = None
    title: Optional[str] = None
    identifier: Optional[str] = None
    path: Optional[str] = None
    bounds: Optional[dict[str, float]] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ActionResult:
    ok: bool
    latency_ms: int
    error: Optional[str] = None
    verified: Optional[bool] = None
    verification_error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LedgerEvent:
    event_id: str
    ts: str
    tool: str
    actor: str
    action: str
    target: ActionTarget
    result: ActionResult
    intent: Optional[IntentPayload] = None
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    prev_hash: Optional[str] = None
    hash: Optional[str] = None
    semantic_status: SemanticStatus = "pending"
    metadata: dict[str, Any] = field(default_factory=dict)

    def compute_hash(self, prev_hash: str) -> str:
        from cortex.utils.canonical import canonical_json, compute_tx_hash

        project = self.metadata.get("project", self.actor)
        detail_json = canonical_json(self.to_canonical_payload())
        return compute_tx_hash(
            prev_hash=prev_hash,
            project=project,
            action=self.action,
            detail_json=detail_json,
            timestamp=self.ts,
        )

    def to_canonical_payload(self) -> dict[str, Any]:
        p = self.to_payload()
        p.pop("hash", None)
        p.pop("prev_hash", None)
        return p

    @staticmethod
    def new(
        *,
        tool: str,
        actor: str,
        action: str,
        target: ActionTarget,
        result: ActionResult,
        intent: Optional[IntentPayload] = None,
        correlation_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> LedgerEvent:
        return LedgerEvent(
            event_id=str(uuid.uuid4()),
            ts=utc_now_iso(),
            tool=tool,
            actor=actor,
            action=action,
            target=target,
            result=result,
            intent=intent,
            correlation_id=correlation_id,
            trace_id=trace_id,
            semantic_status="pending",
            metadata=metadata or {},
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.ts,
            "tool": self.tool,
            "actor": self.actor,
            "action": self.action,
            "target": self.target.to_dict(),
            "result": self.result.to_dict(),
            "intent": self.intent.to_dict() if self.intent else None,
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "prev_hash": self.prev_hash,
            "hash": self.hash,
            "semantic_status": self.semantic_status,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_payload(), ensure_ascii=False, separators=(",", ":"))
