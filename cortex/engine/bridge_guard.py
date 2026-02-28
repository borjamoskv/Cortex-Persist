"""
CORTEX v5.2 — Bridge Validation Guard.

Prevents cross-project contamination by validating bridge facts
before they propagate patterns between projects.

Addresses Cibercentro's core concern: "una vulnerabilidad podría
persistir y propagarse entre proyectos."
"""

from __future__ import annotations

import logging
import re

import aiosqlite

__all__ = ["BridgeGuard"]

logger = logging.getLogger("cortex.bridge_guard")

# Maximum quarantine ratio before bridge is auto-blocked
_QUARANTINE_THRESHOLD = 0.15  # 15% of facts quarantined = contaminated project

# Pattern to extract source project from bridge content
_BRIDGE_SOURCE_RE = re.compile(
    r"(?:from|source|de)\s+(\S+)\s*(?:→|->|to|hacia)",
    re.IGNORECASE,
)


class BridgeGuard:
    """Validates bridge facts before cross-project propagation.

    Security triad completion:
      1. Quarantine — post-facto isolation ✓
      2. Reaper — ghost TTL expiry ✓
      3. BridgeGuard — pre-store prevention ✓
    """

    @staticmethod
    async def validate_bridge(
        conn: aiosqlite.Connection,
        content: str,
        project: str,
        tenant_id: str = "default",
    ) -> dict:
        """Validate a bridge fact before storage.

        Returns:
            dict with keys: allowed (bool), reason (str), source_project (str|None),
            quarantine_ratio (float), meta_flags (dict)
        """
        result = {
            "allowed": True,
            "reason": "",
            "source_project": None,
            "quarantine_ratio": 0.0,
            "meta_flags": {},
        }

        # Extract source project from bridge content
        source = BridgeGuard._extract_source_project(content, project)
        result["source_project"] = source

        if not source:
            # Can't determine source — allow with warning flag
            result["meta_flags"]["bridge_source_unknown"] = True
            logger.debug("Bridge source project unresolvable, allowing with flag")
            return result

        # Check quarantine ratio of source project
        ratio = await BridgeGuard._quarantine_ratio(conn, source, tenant_id)
        result["quarantine_ratio"] = ratio

        if ratio >= _QUARANTINE_THRESHOLD:
            result["allowed"] = False
            result["reason"] = (
                f"Source project '{source}' has {ratio:.0%} quarantined facts "
                f"(threshold: {_QUARANTINE_THRESHOLD:.0%}). Bridge blocked."
            )
            result["meta_flags"]["bridge_blocked"] = True
            result["meta_flags"]["bridge_block_reason"] = "quarantine_threshold"
            logger.warning(
                "🛡️ BRIDGE BLOCKED: %s → %s (quarantine ratio %.0f%%)",
                source, project, ratio * 100,
            )
        elif ratio > 0:
            # Some quarantined facts — allow but flag for review
            result["meta_flags"]["bridge_quarantine_warning"] = True
            result["meta_flags"]["bridge_source_quarantine_ratio"] = round(ratio, 4)
            logger.info(
                "⚠️ Bridge %s → %s has quarantine warnings (ratio %.1f%%)",
                source, project, ratio * 100,
            )

        return result

    @staticmethod
    def _extract_source_project(content: str, target_project: str) -> str | None:
        """Extract source project name from bridge content."""
        # Try regex pattern first
        match = _BRIDGE_SOURCE_RE.search(content)
        if match:
            return match.group(1).strip()

        # Fallback: look for "ProjectA → ProjectB" pattern
        arrow_match = re.search(r"(\S+)\s*(?:→|->)\s*(\S+)", content)
        if arrow_match:
            src, dst = arrow_match.group(1), arrow_match.group(2)
            # Return whichever isn't the target project
            if dst.lower().rstrip(".") == target_project.lower():
                return src.rstrip(".")
            return src.rstrip(".")

        return None

    @staticmethod
    async def _quarantine_ratio(
        conn: aiosqlite.Connection,
        project: str,
        tenant_id: str,
    ) -> float:
        """Calculate quarantine ratio for a project.

        Returns fraction of active facts that are quarantined (0.0 to 1.0).
        """
        cursor = await conn.execute(
            "SELECT "
            "  SUM(CASE WHEN is_quarantined = 1 THEN 1 ELSE 0 END) as quarantined, "
            "  COUNT(*) as total "
            "FROM facts "
            "WHERE tenant_id = ? AND project = ? AND valid_until IS NULL",
            (tenant_id, project),
        )
        row = await cursor.fetchone()
        if not row or not row[1]:
            return 0.0
        return row[0] / row[1]

    @staticmethod
    async def audit_bridges(
        conn: aiosqlite.Connection,
        tenant_id: str = "default",
    ) -> list[dict]:
        """Audit all active bridges for quarantine contamination.

        Returns list of bridge audit results.
        """
        cursor = await conn.execute(
            "SELECT id, project, content FROM facts "
            "WHERE fact_type = 'bridge' AND valid_until IS NULL "
            "AND is_quarantined = 0",
        )
        rows = await cursor.fetchall()

        results = []
        for row in rows:
            fact_id, project, content = row[0], row[1], row[2]
            validation = await BridgeGuard.validate_bridge(
                conn, content, project, tenant_id,
            )
            results.append({
                "fact_id": fact_id,
                "project": project,
                "source_project": validation["source_project"],
                "quarantine_ratio": validation["quarantine_ratio"],
                "allowed": validation["allowed"],
                "reason": validation["reason"],
            })

        return results
