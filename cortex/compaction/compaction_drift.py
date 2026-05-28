"""compaction_drift — Drift Check strategy for the Auto-Compaction Engine.

Extracted from compactor.py to satisfy the Landauer LOC barrier (≤500).
Non-destructive diagnostic: checks L2 vector space topological health.
Does not deprecate or modify any facts — diagnostic only.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.compaction.compactor import CompactionResult
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.compactor.drift")
_LOG_FMT = "Compactor Drift [%s] %s"


async def apply_drift_check(
    engine: CortexEngine,
    project: str,
    result: CompactionResult,
) -> None:
    """Check L2 vector space topological health.

    Non-destructive — appends diagnostic info to result.details only.
    Does not deprecate or modify any facts.
    """
    from cortex.compaction.compactor import CompactionStrategy

    try:
        import numpy as np

        from cortex.memory.drift import DriftMonitor, model_hash_from_name

        embedder = getattr(engine, "_embedder", None)
        model_name = getattr(embedder, "model_name", "all-MiniLM-L6-v2")
        model_hash = model_hash_from_name(model_name)

        conn = await engine.get_conn()
        cursor = await conn.execute(
            "SELECT embedding FROM fact_embeddings "
            "WHERE fact_id IN ("
            "  SELECT id FROM facts WHERE project = ? AND valid_until IS NULL"
            ")",
            (project,),
        )
        rows = await cursor.fetchall()

        if not rows or len(rows) < 10:  # type: ignore[reportArgumentType]
            result.details.append(f"DRIFT_CHECK: insufficient vectors ({len(rows) if rows else 0})")  # type: ignore[reportArgumentType]
            result.strategies_applied.append(str(CompactionStrategy.DRIFT_CHECK.value))
            return

        embeddings = np.array([np.frombuffer(row[0], dtype=np.float32) for row in rows])

        from pathlib import Path  # noqa: F401 — used implicitly by DRIFT_DIR

        from cortex.core.paths import DRIFT_DIR

        monitor = DriftMonitor(model_hash=model_hash, signature_dir=DRIFT_DIR)
        baseline = monitor.load_baseline()

        if baseline is None:
            sig = monitor.checkpoint(embeddings)
            result.details.append(
                f"DRIFT_CHECK: baseline created (n={sig.n_vectors}, "
                f"spectral_gap={sig.spectral_gap:.3f})"
            )
        else:
            health_result = monitor.health(embeddings, baseline)
            health = health_result["topological_health"]
            result.details.append(f"DRIFT_CHECK: health={health:.3f} ({health_result['detail']})")

        result.strategies_applied.append(str(CompactionStrategy.DRIFT_CHECK.value))

    except (ImportError, ValueError, OSError, RuntimeError) as e:
        result.details.append(f"DRIFT_CHECK: skipped ({e})")
        logger.warning(_LOG_FMT, project, f"Drift check failed: {e}")
