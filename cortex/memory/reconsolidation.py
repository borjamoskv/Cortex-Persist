"""CORTEX v8.0 — Memory Reconsolidation v2 (Nader 2000 + Sprint 2 upgrades).

Sprint 2 of the 130/100 plan.

v1 had the core labilization logic but was missing:
  1. Version tracking — no audit trail of reconsolidation events
  2. Confirmation bias detection — LLM could silently rewrite its own history
  3. Tests (zero coverage)
  4. Dream cycle integration hook

v2 adds:
  - ReconsolidationEvent: immutable audit record of every state transition
  - LabilizationRecord.version_id + parent_version: full provenance chain
  - ReconsolidationTracker.audit_trail: O(1) lookup of all events for an engram
  - ConfirmationBiasDetector: flags when confirm/contradict ratio is suspicious
  - dream_sweep() hook: for integration with the dream cycle

Axiom derivation:
  Ω₃ (Byzantine Default): Every state change must be traceable.
  Ω₅ (Antifragile by Default): Track errors to build antibodies, not to hide them.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Final

logger = logging.getLogger("cortex.memory.reconsolidation")

# ─── Constants ────────────────────────────────────────────────────────

# Default labilization window in seconds (5 minutes)
DEFAULT_LABILE_WINDOW_S: Final[float] = 300.0

# Energy penalty for failing to reconsolidate
IGNORE_DECAY: Final[float] = 0.15

# Energy boost for successful reconsolidation
RECONSOLIDATE_BOOST: Final[float] = 0.2

# Max audit events per engram to prevent unbounded growth (Ω₂)
_MAX_AUDIT_EVENTS_PER_ENGRAM: Final[int] = 50

# Confirmation bias threshold: if >80% of events are CONFIRM for a single engram,
# that engram may be getting selectively reinforced (sycophantic bias)
_CONFIRMATION_BIAS_THRESHOLD: Final[float] = 0.80

# Minimum events needed to compute bias score
_BIAS_MIN_EVENTS: Final[int] = 5


# ─── Event Types ─────────────────────────────────────────────────────


class ReconsolidationOutcome(str, Enum):
    """Outcome of a labilization window resolution."""

    CONFIRMED = "confirmed"  # Re-stabilized → energy boost
    CONTRADICTED = "contradicted"  # Content updated → no energy change
    IGNORED = "ignored"  # Window expired → energy penalty


# ─── Audit Record ────────────────────────────────────────────────────


@dataclass(frozen=True)
class ReconsolidationEvent:
    """Immutable audit record of a single reconsolidation state transition.

    Every CONFIRMED / CONTRADICTED / IGNORED resolution produces
    one of these records. They form the version history of an engram.
    """

    event_id: str
    """Unique event identifier (UUID4)."""

    engram_id: str
    """Engram that transitioned."""

    version_id: str
    """New version of the engram post-transition (UUID4)."""

    parent_version: str | None
    """Previous version this supersedes (None = first access)."""

    outcome: ReconsolidationOutcome
    """What happened during the labile window."""

    energy_delta: float
    """Energy change applied: +RECONSOLIDATE_BOOST, 0.0, or -IGNORE_DECAY."""

    resolved_at: float
    """Unix timestamp of resolution."""

    labile_duration_s: float
    """How long the engram was labile before resolution (seconds)."""


# ─── Labilization Record (v2) ────────────────────────────────────────


@dataclass()
class LabilizationRecord:
    """Tracks the labile state of an accessed engram (v2).

    v2 adds: version_id, parent_version for full audit provenance.
    """

    engram_id: str
    accessed_at: float = field(default_factory=time.time)
    window_seconds: float = DEFAULT_LABILE_WINDOW_S
    confirmed: bool = False
    contradicted: bool = False

    # v2 version tracking (Ω₃: every state change is traceable)
    version_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_version: str | None = None

    @property
    def is_expired(self) -> bool:
        """Has the labilization window closed?"""
        return (time.time() - self.accessed_at) > self.window_seconds

    @property
    def is_labile(self) -> bool:
        """Is this engram currently in a labile state?"""
        return not self.is_expired and not self.confirmed and not self.contradicted

    @property
    def age_seconds(self) -> float:
        """How long this record has been alive."""
        return time.time() - self.accessed_at


# ─── Confirmation Bias Detector ──────────────────────────────────────


class ConfirmationBiasDetector:
    """Detects pathological reconsolidation patterns.

    A healthy system should have a mix of CONFIRMED, CONTRADICTED,
    and IGNORED events. A system where >80% of events are CONFIRMED
    for a specific engram is applying sycophantic reinforcement —
    repeatedly confirming a potentially incorrect memory.

    This is the "rewriting history to match biases" problem from the
    original opinion's Section 3: "Sesgo de confirmación."
    """

    __slots__ = ("_confirm_counts", "_total_counts")

    def __init__(self) -> None:
        self._confirm_counts: dict[str, int] = {}
        self._total_counts: dict[str, int] = {}

    def record(self, engram_id: str, outcome: ReconsolidationOutcome) -> None:
        """Record an outcome for bias tracking."""
        self._total_counts[engram_id] = self._total_counts.get(engram_id, 0) + 1
        if outcome == ReconsolidationOutcome.CONFIRMED:
            self._confirm_counts[engram_id] = self._confirm_counts.get(engram_id, 0) + 1

    def bias_score(self, engram_id: str) -> float:
        """Confirmation bias score for an engram [0.0, 1.0].

        1.0 = always confirmed (maximum bias risk).
        0.0 = never confirmed.
        Returns -1.0 if insufficient data.
        """
        total = self._total_counts.get(engram_id, 0)
        if total < _BIAS_MIN_EVENTS:
            return -1.0
        confirms = self._confirm_counts.get(engram_id, 0)
        return round(confirms / total, 4)

    def is_biased(self, engram_id: str) -> bool:
        """True if this engram shows pathological confirmation bias."""
        score = self.bias_score(engram_id)
        return score >= _CONFIRMATION_BIAS_THRESHOLD

    def biased_engrams(self) -> list[str]:
        """All engrams currently showing confirmation bias."""
        return [eid for eid in self._total_counts if self.is_biased(eid)]

    def report(self) -> dict[str, float]:
        """Bias scores for all tracked engrams with sufficient data."""
        return {
            eid: self.bias_score(eid) for eid in self._total_counts if self.bias_score(eid) >= 0
        }


# ─── Reconsolidation Tracker (v2) ────────────────────────────────────


class ReconsolidationTracker:
    """Tracks labile engrams and resolves their fate (v2).

    When an engram is accessed, it enters a labile window.
    The tracker monitors all open windows and resolves them:
    - Confirmed → energy boost (re-stabilization)
    - Contradicted → update content in-place
    - Ignored (window expired) → energy penalty

    v2 enhancements:
    - Full audit trail (list[ReconsolidationEvent] per engram)
    - ConfirmationBiasDetector integration
    - dream_sweep() hook for integration with dream/sleep cycle
    - Previous version ID carried forward in provenance chain
    """

    def __init__(self, window_seconds: float = DEFAULT_LABILE_WINDOW_S) -> None:
        self._window = window_seconds
        self._labile: dict[str, LabilizationRecord] = {}
        # Audit trail: engram_id → list of events (capped at _MAX_AUDIT_EVENTS_PER_ENGRAM)
        self._audit: dict[str, list[ReconsolidationEvent]] = {}
        self._bias_detector = ConfirmationBiasDetector()

    # ─── Access ───────────────────────────────────────────────────

    def on_access(self, engram_id: str, previous_version: str | None = None) -> LabilizationRecord:
        """Mark an engram as labile after access.

        Args:
            engram_id: The engram being accessed.
            previous_version: The version_id of the engram before this access.
                              Pass None if this is the first access.
        """
        record = LabilizationRecord(
            engram_id=engram_id,
            window_seconds=self._window,
            parent_version=previous_version,
        )
        self._labile[engram_id] = record
        logger.debug(
            "Engram %s entered labile state (window=%.0fs, version=%s)",
            engram_id,
            self._window,
            record.version_id[:8],
        )
        return record

    # ─── Resolution ───────────────────────────────────────────────

    def confirm(self, engram_id: str) -> float:
        """Confirm a labile engram → re-stabilize with energy boost.

        Records a CONFIRMED event in the audit trail.
        Returns the energy delta to apply.
        """
        record = self._labile.pop(engram_id, None)
        if record is None or record.is_expired:
            logger.debug("Engram %s confirm attempt outside labile window — ignored.", engram_id)
            return 0.0

        record.confirmed = True
        event = self._make_event(record, ReconsolidationOutcome.CONFIRMED, RECONSOLIDATE_BOOST)
        self._record_audit(event)
        self._bias_detector.record(engram_id, ReconsolidationOutcome.CONFIRMED)

        if self._bias_detector.is_biased(engram_id):
            logger.warning(
                "Engram %s shows confirmation bias (score=%.2f). May be pathologically reinforced.",
                engram_id,
                self._bias_detector.bias_score(engram_id),
            )

        logger.debug(
            "Engram %s RECONSOLIDATED v%s→v%s (boost=+%.2f)",
            engram_id,
            (record.parent_version or "init")[:8],
            event.version_id[:8],
            RECONSOLIDATE_BOOST,
        )
        return RECONSOLIDATE_BOOST

    def contradict(self, engram_id: str) -> float:
        """Contradict a labile engram → flag for in-place content update.

        Records a CONTRADICTED event in the audit trail.
        Returns 0.0 (energy neutral; content gets updated externally).
        """
        record = self._labile.pop(engram_id, None)
        if record is None or record.is_expired:
            logger.debug("Engram %s contradict attempt outside labile window — ignored.", engram_id)
            return 0.0

        record.contradicted = True
        event = self._make_event(record, ReconsolidationOutcome.CONTRADICTED, 0.0)
        self._record_audit(event)
        self._bias_detector.record(engram_id, ReconsolidationOutcome.CONTRADICTED)

        logger.debug(
            "Engram %s CONTRADICTED v%s during labile window.",
            engram_id,
            (record.parent_version or "init")[:8],
        )
        return 0.0

    def sweep(self) -> list[tuple[str, float]]:
        """Sweep expired labile records and apply decay penalties.

        Called every N seconds by the daemon, AND by the dream cycle hook.
        Returns list of (engram_id, energy_delta) for expired records.
        """
        expired: list[tuple[str, float]] = []
        to_remove: list[str] = []

        for eid, record in self._labile.items():
            if record.is_expired and not record.confirmed and not record.contradicted:
                event = self._make_event(record, ReconsolidationOutcome.IGNORED, -IGNORE_DECAY)
                self._record_audit(event)
                self._bias_detector.record(eid, ReconsolidationOutcome.IGNORED)
                expired.append((eid, -IGNORE_DECAY))
                to_remove.append(eid)
                logger.debug(
                    "Engram %s IGNORED during labile window (decay=%.2f, version=%s→%s)",
                    eid,
                    IGNORE_DECAY,
                    (record.parent_version or "init")[:8],
                    event.version_id[:8],
                )

        for eid in to_remove:
            del self._labile[eid]

        if expired:
            logger.info("Reconsolidation sweep: %d engrams decayed.", len(expired))

        return expired

    def dream_sweep(self) -> list[tuple[str, float]]:
        """Dream cycle integration hook — identical to sweep() semantics.

        Called by the dream engine during sleep/offline processing.
        Ensures labile engrams don't accumulate during extended idle periods.

        Returns list of (engram_id, energy_delta) for processed records.
        """
        logger.debug("Dream-cycle reconsolidation sweep initiated.")
        results = self.sweep()
        logger.info("Dream-cycle reconsolidation complete: %d resolved.", len(results))
        return results

    # ─── Audit Trail ──────────────────────────────────────────────

    def audit_trail(self, engram_id: str) -> list[ReconsolidationEvent]:
        """Full version history for an engram. O(1) lookup."""
        return list(self._audit.get(engram_id, []))

    def all_audit_events(self) -> list[ReconsolidationEvent]:
        """All recorded events across all engrams."""
        all_events: list[ReconsolidationEvent] = []
        for events in self._audit.values():
            all_events.extend(events)
        # Sort chronologically
        all_events.sort(key=lambda e: e.resolved_at)
        return all_events

    # ─── Bias Detection ───────────────────────────────────────────

    def confirmation_bias_report(self) -> dict[str, float]:
        """Bias scores for all tracked engrams. (Ω₅: failures forged into antibodies)"""
        return self._bias_detector.report()

    def biased_engrams(self) -> list[str]:
        """Engrams showing pathological confirmation bias."""
        return self._bias_detector.biased_engrams()

    # ─── Properties ───────────────────────────────────────────────

    @property
    def labile_count(self) -> int:
        """Number of currently labile engrams."""
        return len(self._labile)

    @property
    def labile_ids(self) -> list[str]:
        """IDs of currently labile engrams."""
        return list(self._labile.keys())

    @property
    def total_events(self) -> int:
        """Total audit events recorded across all engrams."""
        return sum(len(events) for events in self._audit.values())

    # ─── Internals ────────────────────────────────────────────────

    def _make_event(
        self,
        record: LabilizationRecord,
        outcome: ReconsolidationOutcome,
        energy_delta: float,
    ) -> ReconsolidationEvent:
        """Construct a ReconsolidationEvent from a resolved record."""
        now = time.time()
        return ReconsolidationEvent(
            event_id=str(uuid.uuid4()),
            engram_id=record.engram_id,
            version_id=str(uuid.uuid4()),
            parent_version=record.parent_version,
            outcome=outcome,
            energy_delta=energy_delta,
            resolved_at=now,
            labile_duration_s=now - record.accessed_at,
        )

    def _record_audit(self, event: ReconsolidationEvent) -> None:
        """Append event to the audit trail (bounded by _MAX_AUDIT_EVENTS_PER_ENGRAM)."""
        eid = event.engram_id
        if eid not in self._audit:
            self._audit[eid] = []
        trail = self._audit[eid]
        trail.append(event)
        # Bound per-engram history (Ω₂: entropic asymmetry)
        if len(trail) > _MAX_AUDIT_EVENTS_PER_ENGRAM:
            # Keep the most recent events; discard oldest
            self._audit[eid] = trail[-_MAX_AUDIT_EVENTS_PER_ENGRAM:]

    def __repr__(self) -> str:
        return (
            f"ReconsolidationTracker("
            f"labile={self.labile_count}, "
            f"total_events={self.total_events}, "
            f"biased_engrams={len(self.biased_engrams())})"
        )


# ─── Public API ──────────────────────────────────────────────────────

__all__ = [
    "ConfirmationBiasDetector",
    "DEFAULT_LABILE_WINDOW_S",
    "IGNORE_DECAY",
    "LabilizationRecord",
    "RECONSOLIDATE_BOOST",
    "ReconsolidationEvent",
    "ReconsolidationOutcome",
    "ReconsolidationTracker",
]
