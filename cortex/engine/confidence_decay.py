"""
CORTEX v7 — Confidence Decay Engine.

Downgrades stale `stated` facts through confidence tiers
based on time since last access. Sovereign facts (identity,
axiom, rule) are exempt from decay.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("cortex.decay")

__all__ = ["ConfidenceDecay"]

# Fact types exempt from confidence decay (permanent by nature)
_EXEMPT_TYPES: frozenset[str] = frozenset({
    "identity", "axiom", "rule", "schema", "preference",
})

# Pre-computed SQL fragment — safe: values are compile-time constants
_EXEMPT_PLACEHOLDERS = ",".join("?" for _ in _EXEMPT_TYPES)
_EXEMPT_VALUES = tuple(_EXEMPT_TYPES)

# Decay tiers: (max_age_days, from_confidence, to_confidence)
_DECAY_TIERS: list[tuple[int, str, str]] = [
    (60, "C2", "__deprecate__"),   # C2 → deprecate after 60 days
    (30, "C3", "C2"),              # C3 → C2 after 30 days
    (14, "stated", "C3"),          # stated → C3 after 14 days
]

# Base WHERE clause used by both downgrade and deprecate queries
_WHERE = (
    "WHERE confidence = ? "
    "AND valid_until IS NULL "
    "AND is_quarantined = 0 "
    f"AND fact_type NOT IN ({_EXEMPT_PLACEHOLDERS}) "
    "AND (last_accessed_at IS NULL OR last_accessed_at < ?) "
    "AND created_at < ?"
)


class ConfidenceDecay:
    """Time-based confidence degradation for unverified facts.

    Facts with confidence 'stated' that haven't been accessed
    degrade through C3 → C2 → deprecated over time.
    """

    async def decay(self, conn) -> dict[str, int]:
        """Apply confidence decay to stale facts.

        Returns:
            Dict with counts: downgraded, deprecated.
        """
        now_ts = datetime.now(timezone.utc).isoformat()
        results = {"downgraded": 0, "deprecated": 0}

        for max_days, from_conf, to_conf in _DECAY_TIERS:
            cutoff = (
                datetime.now(timezone.utc) - timedelta(days=max_days)
            ).isoformat()

            if to_conf == "__deprecate__":
                cursor = await conn.execute(
                    f"UPDATE facts SET valid_until = ?, updated_at = ? {_WHERE}",
                    (now_ts, now_ts, from_conf, *_EXEMPT_VALUES, cutoff, cutoff),
                )
                results["deprecated"] += cursor.rowcount
            else:
                cursor = await conn.execute(
                    f"UPDATE facts SET confidence = ?, updated_at = ? {_WHERE}",
                    (to_conf, now_ts, from_conf, *_EXEMPT_VALUES, cutoff, cutoff),
                )
                results["downgraded"] += cursor.rowcount

        await conn.commit()

        total = results["downgraded"] + results["deprecated"]
        if total > 0:
            logger.info(
                "🧬 Confidence decay: %d downgraded, %d deprecated",
                results["downgraded"], results["deprecated"],
            )
        return results
