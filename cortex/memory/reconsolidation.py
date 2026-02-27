"""CORTEX v6+ — Memory Reconsolidation (Nader 2000).

Strategy #4: Every time a memory is accessed, it becomes LABILE
(editable) for a temporal window. If not re-stabilized, it degrades.

This eliminates the problem of obsolete facts persisting because
nobody actively deletes them. Access without confirmation = decay.

Timeline:
  t=0: Memory accessed → marked labile
  t+window: If confirmed → re-stabilize with LTP boost
            If contradicted → update in-place (no duplicate)
            If ignored → energy penalty (soft decay)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger("cortex.memory.reconsolidation")

# Default labilization window in seconds (5 minutes)
DEFAULT_LABILE_WINDOW_S = 300.0

# Energy penalty for failing to reconsolidate
IGNORE_DECAY = 0.15

# Energy boost for successful reconsolidation
RECONSOLIDATE_BOOST = 0.2


@dataclass(slots=True)
class LabilizationRecord:
    """Tracks the labile state of an accessed engram."""

    engram_id: str
    accessed_at: float = field(default_factory=time.time)
    window_seconds: float = DEFAULT_LABILE_WINDOW_S
    confirmed: bool = False
    contradicted: bool = False

    @property
    def is_expired(self) -> bool:
        """Has the labilization window closed?"""
        return (time.time() - self.accessed_at) > self.window_seconds

    @property
    def is_labile(self) -> bool:
        """Is this engram currently in a labile state?"""
        return not self.is_expired and not self.confirmed and not self.contradicted


class ReconsolidationTracker:
    """Tracks labile engrams and resolves their fate.

    When an engram is accessed, it enters a labile window.
    The tracker monitors all open windows and resolves them:
    - Confirmed → energy boost (re-stabilization)
    - Contradicted → update content in-place
    - Ignored (window expired) → energy penalty
    """

    def __init__(self, window_seconds: float = DEFAULT_LABILE_WINDOW_S):
        self._window = window_seconds
        self._labile: dict[str, LabilizationRecord] = {}

    def on_access(self, engram_id: str) -> LabilizationRecord:
        """Mark an engram as labile after access."""
        record = LabilizationRecord(
            engram_id=engram_id,
            window_seconds=self._window,
        )
        self._labile[engram_id] = record
        logger.debug(
            "Engram %s entered labile state (window=%.0fs)",
            engram_id,
            self._window,
        )
        return record

    def confirm(self, engram_id: str) -> float:
        """Confirm a labile engram → re-stabilize with boost.

        Returns the energy delta to apply.
        """
        record = self._labile.pop(engram_id, None)
        if record is None or record.is_expired:
            return 0.0

        record.confirmed = True
        logger.debug("Engram %s RECONSOLIDATED (boost=+%.2f)", engram_id, RECONSOLIDATE_BOOST)
        return RECONSOLIDATE_BOOST

    def contradict(self, engram_id: str) -> float:
        """Contradict a labile engram → flag for in-place update.

        Returns the energy delta (neutral for contradictions).
        """
        record = self._labile.pop(engram_id, None)
        if record is None or record.is_expired:
            return 0.0

        record.contradicted = True
        logger.debug("Engram %s CONTRADICTED during labile window", engram_id)
        return 0.0  # Energy stays neutral; content gets updated externally

    def sweep(self) -> list[tuple[str, float]]:
        """Sweep expired labile records and apply decay penalties.

        Returns list of (engram_id, energy_delta) for expired records.
        """
        expired: list[tuple[str, float]] = []
        to_remove: list[str] = []

        for eid, record in self._labile.items():
            if record.is_expired and not record.confirmed and not record.contradicted:
                expired.append((eid, -IGNORE_DECAY))
                to_remove.append(eid)
                logger.debug(
                    "Engram %s IGNORED during labile window (decay=%.2f)",
                    eid,
                    IGNORE_DECAY,
                )

        for eid in to_remove:
            del self._labile[eid]

        return expired

    @property
    def labile_count(self) -> int:
        """Number of currently labile engrams."""
        return len(self._labile)

    @property
    def labile_ids(self) -> list[str]:
        """IDs of currently labile engrams."""
        return list(self._labile.keys())
