"""CORTEX v7 — Sovereign Safety Invariants.

Defines the mathematical properties that no RSI mutation may ever violate.
These are used by the FormalVerificationGate (Z3) to validate code before commit.
"""

from enum import Enum
from typing import NamedTuple


class InvariantSeverity(Enum):
    CRITICAL = "critical"  # Immediate rollback, high-level alert
    WARNING = "warning"  # Log and notify, but may allow with caution
    INFO = "info"  # Best practice recommendation


class SafetyInvariant(NamedTuple):
    id: str
    name: str
    description: str
    severity: InvariantSeverity = InvariantSeverity.CRITICAL


SOVEREIGN_INVARIANTS = [
    SafetyInvariant(
        id="I1",
        name="Tenant Isolation",
        description="∀ query q, result r: r.tenant_id == q.tenant_id. Cross-tenant leakage is prohibited.",
    ),
    SafetyInvariant(
        id="I2",
        name="Ledger Append-Only",
        description="∀ transaction tx: No DELETE or UPDATE operations allowed on L3 event records.",
    ),
    SafetyInvariant(
        id="I3",
        name="Hash Chain Integrity",
        description="∀ block b[i]: b[i].prev_hash == hash(b[i-1]). The Merkle state must remain consistent.",
    ),
    SafetyInvariant(
        id="I4",
        name="Encryption Preservation",
        description="∀ fact f: f.content must be encrypted at rest unless explicitly marked for FTS.",
    ),
    SafetyInvariant(
        id="I5",
        name="No Unbounded Collections",
        description="∀ collection c: len(c) ≤ MAX_LIMIT. Prevents memory exhaustion attacks.",
    ),
    SafetyInvariant(
        id="I6",
        name="Idempotent Operations",
        description="∀ operation op(x): op(op(x)) == op(x). All API and store mutations must be retry-safe.",
    ),
    SafetyInvariant(
        id="I7",
        name="Termination Guarantee",
        description="∀ loop L: ∃ variant v such that v strictly decreases per iteration. Prohibits infinite RSI loops.",
    ),
]
