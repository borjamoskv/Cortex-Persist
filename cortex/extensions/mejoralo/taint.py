"""Taint Circuit Breaker for MEJORAlo.

Extracted from heal.py to maintain thermodynamic LOC limits.
"""

import logging
from typing import Optional, TYPE_CHECKING

from cortex.extensions.mejoralo.constants import TAINT_TAG

if TYPE_CHECKING:
    from cortex.extensions.mejoralo.engine import MejoraloEngine

logger = logging.getLogger("cortex.extensions.mejoralo.taint")

def mark_file_tainted(
    file_path: str,
    project: str,
    engine: Optional['MejoraloEngine'],
) -> None:
    """Persist a permanent Taint mark on a file that failed L3 healing."""
    if not engine or not project:
        return
    logger.warning("[TAINT] Marking %s as permanently tainted in CORTEX.", file_path)
    try:
        engine.engine.store_sync(
            project=project,
            content=(
                f"[MEJORAlo TAINT] {file_path} failed L3 healing. "
                "Requires ariadne-arch-omega intervention before retry."
            ),
            fact_type="error",
            tags=["mejoralo", TAINT_TAG, "circuit-breaker"],
            confidence="verified",
            source="cortex-mejoralo",
            meta={"file_path": file_path, "tainted": True},
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to persist taint for %s", file_path)

def is_file_tainted(
    file_path: str,
    project: str,
    engine: Optional['MejoraloEngine'],
) -> bool:
    """Check if a file has been permanently tainted in CORTEX."""
    if not engine or not project:
        return False
    try:
        scars = engine.scars(project, file_path, limit=10)
        return any(TAINT_TAG in (s.get("content", "")) for s in scars)
    except Exception:  # noqa: BLE001
        return False
