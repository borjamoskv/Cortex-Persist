# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class SortuState(str, Enum):
    DRAFT = "DRAFT"
    AUDITED = "AUDITED"
    FORGED = "FORGED"
    VERIFIED = "VERIFIED"
    LINKED = "LINKED"
    LEDGERED = "LEDGERED"
    ACTIVE = "ACTIVE"
    ABORTED = "ABORTED"
    QUARANTINED = "QUARANTINED"
    TOMBSTONED = "TOMBSTONED"
    PURGED = "PURGED"


TRANSITIONS: dict[SortuState, list[SortuState]] = {
    SortuState.DRAFT: [SortuState.AUDITED, SortuState.ABORTED],
    SortuState.AUDITED: [SortuState.FORGED, SortuState.ABORTED],
    SortuState.FORGED: [SortuState.VERIFIED, SortuState.ABORTED],
    SortuState.VERIFIED: [SortuState.LINKED, SortuState.ABORTED],
    SortuState.LINKED: [SortuState.LEDGERED, SortuState.ABORTED],
    SortuState.LEDGERED: [SortuState.ACTIVE, SortuState.ABORTED],
    SortuState.ACTIVE: [SortuState.QUARANTINED],
    SortuState.ABORTED: [],
    SortuState.QUARANTINED: [SortuState.ACTIVE, SortuState.TOMBSTONED],
    SortuState.TOMBSTONED: [SortuState.PURGED],
    SortuState.PURGED: [],
}


def validate_transition(from_state: SortuState, to_state: SortuState) -> bool:
    return to_state in TRANSITIONS[from_state]


class AbortReason(str, Enum):
    REDUNDANT_COMPUTATION = "REDUNDANT_COMPUTATION"
    CONTRACT_VERIFICATION_FAILED = "CONTRACT_VERIFICATION_FAILED"
    INVALID_CAUSAL_PARENT = "INVALID_CAUSAL_PARENT"


class ForgeAbortError(RuntimeError):
    def __init__(self, reason: AbortReason, detail: str = "") -> None:
        self.reason = reason
        message = reason.value
        if detail:
            message = f"{message}: {detail}"
        super().__init__(message)


@dataclass(frozen=True)
class YieldEvent:
    hours_saved: float
    days_since: int
    verified: bool = False


@dataclass(frozen=True)
class ForgeInvocation:
    intent: str
    causal_parent: str | None
    requested_by: str
    overlap_threshold: float = 0.9
    causal_gap_threshold: float = 0.15
    ttl_days: int = 7

    def __post_init__(self) -> None:
        if len(self.intent.strip()) < 8:
            raise ValueError("intent must be at least 8 characters long")
        if not self.requested_by.strip():
            raise ValueError("requested_by cannot be empty")
        if not 0.0 <= self.overlap_threshold <= 1.0:
            raise ValueError("overlap_threshold must be between 0 and 1")
        if not 0.0 <= self.causal_gap_threshold <= 1.0:
            raise ValueError("causal_gap_threshold must be between 0 and 1")
        if self.ttl_days < 0:
            raise ValueError("ttl_days must be >= 0")


@dataclass
class SkillRecord:
    skill_id: str
    skill_name: str
    version: str
    artifact_hashes: dict[str, str]
    state: SortuState
    created_at: datetime
    ttl_expiration: datetime
    causal_parent: str | None = None
    purge_status: str = "NONE"
    abort_reason: AbortReason | None = None
    verification_status: str | None = None
    yield_events: list[YieldEvent] = field(default_factory=list)

    @classmethod
    def new(
        cls,
        skill_name: str,
        version: str,
        artifact_hashes: dict[str, str],
        *,
        causal_parent: str | None = None,
        ttl_days: int = 7,
    ) -> SkillRecord:
        now = _now_utc()
        return cls(
            skill_id=str(uuid.uuid4()),
            skill_name=skill_name,
            version=version,
            artifact_hashes=dict(artifact_hashes),
            state=SortuState.DRAFT,
            created_at=now,
            ttl_expiration=now + timedelta(days=ttl_days),
            causal_parent=causal_parent,
        )
