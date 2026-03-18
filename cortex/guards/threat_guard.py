"""ThreatGuard — Epistemic Quarantine for Hostile/External Vectors (Moltbook-Omega).

Axiom Ω₂: Causal Taint Trade-Off. Entropy bleed from adversarial environments
must be tagged and isolated (Taint Propagation) so that internal reasoning chains
are not polluted by external Zalgo DDOS or hostile prompt injections.
"""

from typing import Any


class ThreatGuard:
    """Isolates and tags incoming hostile external data."""

    HOSTILE_SOURCES = (
        "external:hostile",
        "agent:moltbook-omega",
        "moltbook:feed",
        "moltbook:reply",
    )

    @classmethod
    def apply_quarantine(cls, source: str | None, meta: dict[str, Any] | None) -> dict[str, Any]:
        """Mark meta as tainted if source matches hostile profiles."""
        if not source:
            return meta or {}

        is_hostile = False
        for hs in cls.HOSTILE_SOURCES:
            if source.startswith(hs):
                is_hostile = True
                break

        if is_hostile:
            meta = meta or {}
            # Propagate the Taint
            meta["tainted"] = True
            meta["quarantine_reason"] = "Epistemic Isolation (ThreatGuard)"
            # Force lowest confidence for external noise to limit blast radius
            meta["confidence"] = "C1"

        return meta or {}
