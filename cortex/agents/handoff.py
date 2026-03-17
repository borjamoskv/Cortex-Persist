"""
CORTEX Agent Handoff v1.3 — Sovereign context transfer protocol.

Provides structured context snapshots for agent-to-agent handoff,
including cognitive fingerprint for epistemic continuity.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

HANDOFF_VERSION = "1.3"

__all__ = ["HANDOFF_VERSION", "generate_handoff", "HandoffContext"]


class HandoffContext:
    """
    Encapsulates the full epistemic state required for a clean agent handoff.

    Attributes:
        version: Protocol version (must match HANDOFF_VERSION).
        timestamp: UTC epoch when snapshot was taken.
        cognitive_fingerprint: SHA-256 of the serialized context for integrity.
        payload: Arbitrary agent-specific state dict.
    """

    def __init__(self, payload: dict[str, Any]) -> None:
        self.version = HANDOFF_VERSION
        self.timestamp = time.time()
        self.payload = payload
        self.cognitive_fingerprint = self._compute_fingerprint()

    def _compute_fingerprint(self) -> str:
        """SHA-256 fingerprint of the payload for integrity verification."""
        raw = str(sorted(self.payload.items())).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "cognitive_fingerprint": self.cognitive_fingerprint,
            "payload": self.payload,
        }


def generate_handoff(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Generate a v1.3 handoff context dict with cognitive fingerprint.

    Args:
        payload: The agent state to transfer.

    Returns:
        A serializable dict containing version, timestamp,
        cognitive_fingerprint, and the payload.
    """
    ctx = HandoffContext(payload)
    return ctx.to_dict()
