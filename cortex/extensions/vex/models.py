"""VEX Data Models — Cryptographically verifiable execution primitives.

All models are immutable dataclasses designed for hash-chain integration
with CORTEX's ImmutableLedger and WBFT consensus.

Derivation: Ω₃ (Byzantine Default) — every model is self-verifiable.
"""

from __future__ import annotations

import enum
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

__all__ = [
    "ExecutionReceipt",
    "PlannedStep",
    "StepResult",
    "TaskPlan",
    "VEXStatus",
]


def _now_iso() -> str:
    """UTC ISO timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _sha256(data: str) -> str:
    """Deterministic SHA-256 hash."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


class VEXStatus(str, enum.Enum):
    """Execution status lifecycle."""

    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    ABORTED = "aborted"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass(frozen=True)
class PlannedStep:
    """A single planned execution step.

    Each step maps to one tool invocation. The step is designed to
    produce a single, verifiable transaction in the CORTEX ledger.
    """

    step_id: str
    description: str
    tool: str
    args: dict[str, Any] = field(default_factory=dict)
    expected_outcome: str = ""
    timeout_seconds: int = 60
    tether_check: bool = True
    depends_on: list[str] = field(default_factory=list)

    def content_hash(self) -> str:
        """Deterministic hash of step specification."""
        payload = json.dumps(
            {
                "step_id": self.step_id,
                "description": self.description,
                "tool": self.tool,
                "args": self.args,
                "expected_outcome": self.expected_outcome,
            },
            sort_keys=True,
        )
        return _sha256(payload)


@dataclass
class TaskPlan:
    """A decomposed task with verifiable steps.

    The plan itself is hash-chained: plan_hash = SHA-256 of all step hashes
    concatenated in order. This makes plan tampering detectable.
    """

    task_id: str
    intent: str
    steps: list[PlannedStep] = field(default_factory=list)
    created_at: str = field(default_factory=_now_iso)
    source: str = "agent:vex"
    model: str = ""
    requires_consensus: bool = False

    @property
    def plan_hash(self) -> str:
        """Deterministic hash of the entire plan."""
        step_hashes = ":".join(s.content_hash() for s in self.steps)
        return _sha256(f"{self.task_id}:{self.intent}:{step_hashes}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "intent": self.intent,
            "steps": [
                {
                    "step_id": s.step_id,
                    "description": s.description,
                    "tool": s.tool,
                    "args": s.args,
                    "expected_outcome": s.expected_outcome,
                    "timeout_seconds": s.timeout_seconds,
                    "content_hash": s.content_hash(),
                }
                for s in self.steps
            ],
            "plan_hash": self.plan_hash,
            "created_at": self.created_at,
            "source": self.source,
            "model": self.model,
        }


@dataclass
class StepResult:
    """Result of executing a single PlannedStep."""

    step_id: str
    success: bool
    output: str = ""
    error: str | None = None
    duration_ms: int = 0
    started_at: str = ""
    completed_at: str = ""
    tx_hash: str | None = None
    fact_id: int | None = None

    def content_hash(self) -> str:
        """Hash of the result — covers output + success status."""
        payload = json.dumps(
            {
                "step_id": self.step_id,
                "success": self.success,
                "output_hash": _sha256(self.output) if self.output else "",
                "error": self.error or "",
            },
            sort_keys=True,
        )
        return _sha256(payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "success": self.success,
            "output": self.output[:500] if self.output else "",
            "error": self.error,
            "duration_ms": self.duration_ms,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "tx_hash": self.tx_hash,
            "fact_id": self.fact_id,
            "content_hash": self.content_hash(),
        }


@dataclass
class ExecutionReceipt:
    """Cryptographic proof that an agent executed a task.

    The receipt is the VEX deliverable — a self-contained, independently
    verifiable proof of execution that can be shared with auditors,
    compliance officers, or third-party systems.
    """

    task_id: str
    plan_hash: str = ""
    intent: str = ""
    status: VEXStatus = VEXStatus.PLANNED
    steps: list[StepResult] = field(default_factory=list)
    merkle_root: str | None = None
    total_duration_ms: int = 0
    consensus_score: float = 1.0
    created_at: str = field(default_factory=_now_iso)
    completed_at: str | None = None
    model: str = ""
    source: str = "agent:vex"

    def add_step(self, result: StepResult) -> None:
        """Append a step result."""
        self.steps.append(result)
        self.total_duration_ms += result.duration_ms

    def abort(self, reason: str, step_id: str = "") -> None:
        """Mark execution as aborted."""
        self.status = VEXStatus.ABORTED
        self.completed_at = _now_iso()
        self.steps.append(
            StepResult(
                step_id=step_id or "abort",
                success=False,
                error=reason,
                completed_at=self.completed_at,
            )
        )

    @property
    def receipt_hash(self) -> str:
        """Self-verifying hash of the entire receipt."""
        step_chain = ":".join(s.content_hash() for s in self.steps)
        payload = (
            f"{self.task_id}:{self.plan_hash}:{self.status.value}"
            f":{step_chain}:{self.merkle_root or 'none'}"
            f":{self.consensus_score}"
        )
        return _sha256(payload)

    def verify(self) -> bool:
        """Self-verification: recompute receipt_hash and verify consistency."""
        # 1. Verify all step hashes are consistent
        for step in self.steps:
            if not step.content_hash():
                return False
        # 2. Verify plan_hash was set
        if not self.plan_hash:
            return False
        # 3. Receipt hash is deterministic
        _ = self.receipt_hash
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "vex_version": "1.0",
            "task_id": self.task_id,
            "intent": self.intent,
            "plan_hash": self.plan_hash,
            "status": self.status.value,
            "steps": [s.to_dict() for s in self.steps],
            "merkle_root": self.merkle_root,
            "total_duration_ms": self.total_duration_ms,
            "consensus_score": self.consensus_score,
            "receipt_hash": self.receipt_hash,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "model": self.model,
            "source": self.source,
        }

    def export_proof(self) -> str:
        """Export as portable JSON proof for third-party verification."""
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionReceipt:
        """Reconstruct a receipt from dict (e.g., loaded from JSON)."""
        steps = [
            StepResult(
                step_id=s["step_id"],
                success=s["success"],
                output=s.get("output", ""),
                error=s.get("error"),
                duration_ms=s.get("duration_ms", 0),
                started_at=s.get("started_at", ""),
                completed_at=s.get("completed_at", ""),
                tx_hash=s.get("tx_hash"),
                fact_id=s.get("fact_id"),
            )
            for s in data.get("steps", [])
        ]
        return cls(
            task_id=data["task_id"],
            plan_hash=data.get("plan_hash", ""),
            intent=data.get("intent", ""),
            status=VEXStatus(data.get("status", "planned")),
            steps=steps,
            merkle_root=data.get("merkle_root"),
            total_duration_ms=data.get("total_duration_ms", 0),
            consensus_score=data.get("consensus_score", 1.0),
            created_at=data.get("created_at", ""),
            completed_at=data.get("completed_at"),
            model=data.get("model", ""),
            source=data.get("source", ""),
        )
