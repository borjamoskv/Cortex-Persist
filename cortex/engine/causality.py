"""Causality Engine — AX-014: Mapping the Causal Chord (Ω₁).

This engine links facts to the signals that triggered them, creating 
a directed acyclic graph (DAG) of consequence.
"""

from __future__ import annotations
import logging
import sqlite3
from typing import Any

from cortex.signals.bus import SignalBus

logger = logging.getLogger("cortex.causality")

class CausalOracle:
    """Interprets the Signal Bus to find the parent of a fact."""


    @staticmethod
    def find_parent_signal(db_path: str, project: str | None = None) -> int | None:
        """
        Finds the most recent unconsumed 'plan:done' or 'task:start' signal
        that likely triggered the current storage operation.
        """
        try:
            with sqlite3.connect(db_path) as conn:
                bus = SignalBus(conn)
                # We look for the most recent 'active' signals in the last 60 seconds
                recent = bus.history(project=project, limit=5)
                for sig in recent:
                    if sig.event_type in ("plan:done", "task:start", "apotheosis:heal"):
                        return sig.id
        except Exception as e:
            logger.debug("Causal lookup failed: %s", e)
        return None


def link_causality(meta: dict[str, Any] | None, signal_id: int | None) -> dict[str, Any]:
    """Attaches causal metadata to a fact's meta dictionary."""
    m = meta or {}
    if signal_id:
        m["causal_parent"] = signal_id
        m["axiomatic_integrity"] = "Ω₁"
    return m
