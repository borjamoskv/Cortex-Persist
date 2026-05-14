"""CORTEX v8.0 — Crystal Consolidator (REM Sleep Phase).

The destructive half of the NightShift cycle. Executes 4 consolidation
strategies on crystals based on their CrystalVitals assessment:

    1. COLD_PURGE     — Remove dead weight (cold + irrelevant + old)
    2. SEMANTIC_MERGE  — Fuse near-duplicate crystals (cosine > 0.92)
    3. DIAMOND_PROMOTE — Elevate high-impact crystals to immortal status
    4. RE_EMBED        — Refresh stale embeddings with current encoder

Axiom Derivations:
    Ω₂ (Entropic Asymmetry): Purging reduces noise, increasing recall precision.
    Ω₅ (Antifragile): Each purge forges an antibody — the radar learns to avoid
        targets that produce dead weight.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from cortex.extensions.swarm.crystal_thermometer import CrystalVitals

logger = logging.getLogger("cortex.extensions.swarm.crystal_consolidator")

# ── Thresholds ────────────────────────────────────────────────────────────

SEMANTIC_MERGE_THRESHOLD = 0.92  # Cosine similarity for merge
MIN_AGE_FOR_PURGE_DAYS = 14
MIN_AGE_FOR_PROMOTE_DAYS = 7
RE_EMBED_AGE_DAYS = 30


# ── Result Model ──────────────────────────────────────────────────────────


@dataclass
class ConsolidationResult:
    """Outcome of a consolidation cycle."""

    purged: int = 0
    merged: int = 0
    promoted: int = 0
    re_embedded: int = 0
    skipped: int = 0
    errors: int = 0
    total_scanned: int = 0
    dry_run: bool = False
    details: list[str] | None = None

    @property
    def total_actions(self) -> int:
        return self.purged + self.merged + self.promoted + self.re_embedded

    def to_dict(self) -> dict[str, Any]:
        return {
            "purged": self.purged,
            "merged": self.merged,
            "promoted": self.promoted,
            "re_embedded": self.re_embedded,
            "skipped": self.skipped,
            "errors": self.errors,
            "total_scanned": self.total_scanned,
            "total_actions": self.total_actions,
            "dry_run": self.dry_run,
        }


# ── Strategy 1: Cold Purge ────────────────────────────────────────────────


async def _execute_cold_purge(
    db_conn: Any,
    vitals: list[CrystalVitals],
    result: ConsolidationResult,
    dry_run: bool,
) -> None:
    """Remove dead weight crystals (cold + irrelevant + old + not diamond)."""
    purge_candidates = [
        v
        for v in vitals
        if v.recommendation == "PURGE" and v.age_days >= MIN_AGE_FOR_PURGE_DAYS and not v.is_diamond
    ]

    if not purge_candidates:
        return

    logger.info("🗑️ [CONSOLIDATOR] Cold purge: %d candidates", len(purge_candidates))

    if dry_run:
        for v in purge_candidates:
            result.purged += 1
            logger.info(
                "🗑️ [PURGE] %s — temp=%.3f, res=%.3f, age=%.0fd (DRY)",
                v.fact_id,
                v.temperature,
                v.resonance,
                v.age_days,
            )
        return

    try:
        cursor = db_conn.cursor()

        # Process in chunks of 900 to respect SQLite parameter limits
        chunk_size = 900
        for i in range(0, len(purge_candidates), chunk_size):
            chunk = purge_candidates[i : i + chunk_size]

            # 1. Soft delete: update metadata
            update_params = [(time.time(), v.temperature, v.resonance, v.fact_id) for v in chunk]
            cursor.executemany(
                """
                UPDATE facts_meta
                SET metadata = json_set(COALESCE(metadata, '{}'),
                    '$.nightshift_purged', ?,
                    '$.purge_reason', 'cold_dead_weight',
                    '$.purge_temperature', ?,
                    '$.purge_resonance', ?)
                WHERE id = ?
                """,
                update_params,
            )

            # 2. Actually remove from vector index for recall hygiene
            chunk_ids = [v.fact_id for v in chunk]
            placeholders = ",".join("?" for _ in chunk_ids)

            cursor.execute(
                f"DELETE FROM vec_facts WHERE rowid IN "
                f"(SELECT rowid FROM facts_meta WHERE id IN ({placeholders}))",
                chunk_ids,
            )

            # 3. Delete from facts_meta
            cursor.execute(
                f"DELETE FROM facts_meta WHERE id IN ({placeholders})",
                chunk_ids,
            )

            db_conn.commit()

            for v in chunk:
                result.purged += 1
                logger.info(
                    "🗑️ [PURGE] %s — temp=%.3f, res=%.3f, age=%.0fd",
                    v.fact_id,
                    v.temperature,
                    v.resonance,
                    v.age_days,
                )

    except (sqlite3.Error, ValueError, TypeError) as e:
        logger.error("🗑️ [PURGE] Database error during bulk purge: %s", e)
        # Add to errors approximately since we batch
        result.errors += len(purge_candidates) - result.purged


# ── Strategy 2: Semantic Merge ────────────────────────────────────────────


async def _execute_semantic_merge(
    db_conn: Any,
    vitals: list[CrystalVitals],
    result: ConsolidationResult,
    dry_run: bool,
) -> None:
    """Merge near-duplicate crystals (cosine > threshold).

    Uses LLM synthesis to fuse content if they are highly similar,
    preserving unique details from both. Vectorized to eliminate O(N^2) Python loops.
    """
    from cortex.extensions.swarm.crystal_synthesis import synthesize_crystals
    import asyncio

    # Only merge crystals that have embeddings available
    mergeable = [v for v in vitals if v.recommendation != "PURGE"]
    if len(mergeable) < 2:
        return

    # Load content and embeddings in batches to prevent N+1
    data: dict[str, dict[str, Any]] = {}
    try:
        cursor = db_conn.cursor()
        chunk_size = 900
        mergeable_ids = [v.fact_id for v in mergeable]

        for i in range(0, len(mergeable_ids), chunk_size):
            chunk_ids = mergeable_ids[i : i + chunk_size]
            placeholders = ",".join("?" for _ in chunk_ids)

            cursor.execute(
                f"""
                SELECT f.id, f.content, v.embedding FROM facts_meta f
                JOIN vec_facts v ON f.rowid = v.rowid
                WHERE f.id IN ({placeholders})
                """,
                chunk_ids,
            )
            for row in cursor.fetchall():
                data[row[0]] = {
                    "content": row[1],
                    "embedding": np.frombuffer(row[2], dtype=np.float32),
                }
    except (sqlite3.Error, ValueError, TypeError) as e:
        logger.error("🔗 [MERGE] Failed to load data: %s", e)
        return

    if len(data) < 2:
        return

    # Vectorized similarity computation
    ids = list(data.keys())
    embeddings = [data[id_]["embedding"] for id_ in ids]

    # Stack and normalize
    try:
        X = np.vstack(embeddings)
        norms = np.linalg.norm(X, axis=1, keepdims=True)
        # Avoid division by zero
        norms[norms < 1e-10] = 1.0
        X_norm = X / norms

        # Compute full similarity matrix
        sim_matrix = np.dot(X_norm, X_norm.T)
    except Exception as e:
        logger.error("🔗 [MERGE] Matrix computation failed: %s", e)
        return

    # Extract upper triangular indices where similarity >= threshold
    # k=1 excludes the diagonal
    rows, cols = np.where(np.triu(sim_matrix, k=1) >= SEMANTIC_MERGE_THRESHOLD)

    # Filter overlapping pairs to ensure we only process independent merges in one pass
    merged_ids: set[str] = set()
    independent_pairs = []

    for r, c in zip(rows, cols, strict=False):
        id_a, id_b = ids[r], ids[c]
        if id_a not in merged_ids and id_b not in merged_ids:
            sim = float(sim_matrix[r, c])
            independent_pairs.append((id_a, id_b, sim))
            # Mark both as processed for this cycle
            merged_ids.add(id_a)
            merged_ids.add(id_b)

    if not independent_pairs:
        return

    logger.info("🔗 [MERGE] Found %d independent collision pairs", len(independent_pairs))

    # Concurrent LLM synthesis execution
    semaphore = asyncio.Semaphore(5)

    async def _safe_synthesize(id_a: str, id_b: str, sim: float) -> tuple[str, str, str | None]:
        async with semaphore:
            try:
                logger.info("🔗 [MERGE] Collided: %s (~%.4f) %s", id_a, sim, id_b)
                synthesis = await synthesize_crystals(
                    primary_content=data[id_a]["content"],
                    secondary_content=data[id_b]["content"],
                )
                new_content = synthesis.get("fused_content", data[id_a]["content"])
                return id_a, id_b, new_content
            except (ValueError, TypeError, RuntimeError) as e:
                logger.error("🔗 [MERGE] Synthesis failed for %s/%s: %s", id_a, id_b, e)
                return id_a, id_b, None

    synthesis_tasks = [_safe_synthesize(id_a, id_b, sim) for id_a, id_b, sim in independent_pairs]

    # Gather all results
    synthesis_results = await asyncio.gather(*synthesis_tasks)

    successful_merges = [
        (id_a, id_b, new_content)
        for id_a, id_b, new_content in synthesis_results
        if new_content is not None
    ]

    if not successful_merges:
        result.errors += len(independent_pairs)
        return

    result.errors += len(independent_pairs) - len(successful_merges)

    if dry_run:
        for id_a, id_b, _ in successful_merges:
            result.merged += 1
            logger.info("🧪 [SYNTHESIS] %s + %s → Unified Crystal (DRY)", id_a, id_b)
        return

    # Batch database updates
    try:
        cursor = db_conn.cursor()
        current_time = time.time()

        # 1. Update primaries
        update_params = [
            (new_content, current_time, id_a) for id_a, _, new_content in successful_merges
        ]
        cursor.executemany(
            "UPDATE facts_meta SET content = ?, timestamp = ? WHERE id = ?",
            update_params,
        )

        # 2. Delete secondaries
        secondary_ids = [id_b for _, id_b, _ in successful_merges]

        chunk_size = 900
        for i in range(0, len(secondary_ids), chunk_size):
            chunk_ids = secondary_ids[i : i + chunk_size]
            placeholders = ",".join("?" for _ in chunk_ids)

            cursor.execute(
                f"DELETE FROM vec_facts WHERE rowid IN "
                f"(SELECT rowid FROM facts_meta WHERE id IN ({placeholders}))",
                chunk_ids,
            )
            cursor.execute(
                f"DELETE FROM facts_meta WHERE id IN ({placeholders})",
                chunk_ids,
            )

        db_conn.commit()

        for id_a, id_b, _ in successful_merges:
            result.merged += 1
            logger.info("🧪 [SYNTHESIS] %s + %s → Unified Crystal", id_a, id_b)

    except (sqlite3.Error, ValueError, TypeError) as e:
        logger.error("🔗 [MERGE] Database error during batch merge update: %s", e)
        result.errors += len(successful_merges)


# ── Strategy 3: Diamond Promotion ─────────────────────────────────────────


async def _execute_diamond_promotion(
    db_conn: Any,
    vitals: list[CrystalVitals],
    result: ConsolidationResult,
    dry_run: bool,
) -> None:
    """Promote high-impact crystals to diamond (immune to decay)."""
    promote_candidates = [
        v
        for v in vitals
        if v.recommendation in ("PROMOTE", "PROTECT")
        and not v.is_diamond
        and v.age_days >= MIN_AGE_FOR_PROMOTE_DAYS
    ]

    if not promote_candidates:
        return

    logger.info("💎 [CONSOLIDATOR] Diamond promotion: %d candidates", len(promote_candidates))

    if dry_run:
        for v in promote_candidates:
            result.promoted += 1
            logger.info(
                "💎 [PROMOTE] %s → DIAMOND (temp=%.3f, res=%.3f) (DRY)",
                v.fact_id,
                v.temperature,
                v.resonance,
            )
        return

    try:
        cursor = db_conn.cursor()
        chunk_size = 900

        for i in range(0, len(promote_candidates), chunk_size):
            chunk = promote_candidates[i : i + chunk_size]
            chunk_ids = [v.fact_id for v in chunk]
            placeholders = ",".join("?" for _ in chunk_ids)

            cursor.execute(
                f"UPDATE facts_meta SET is_diamond = 1 WHERE id IN ({placeholders})",
                chunk_ids,
            )
            db_conn.commit()

            for v in chunk:
                result.promoted += 1
                logger.info(
                    "💎 [PROMOTE] %s → DIAMOND (temp=%.3f, res=%.3f)",
                    v.fact_id,
                    v.temperature,
                    v.resonance,
                )

    except (sqlite3.Error, ValueError, TypeError) as e:
        logger.error("💎 [PROMOTE] Database error during batch promotion: %s", e)
        # Approximate errors
        result.errors += len(promote_candidates) - result.promoted


# ── Public API ────────────────────────────────────────────────────────────


async def consolidate(
    db_conn: Any,
    vitals: list[CrystalVitals],
    dry_run: bool = False,
) -> ConsolidationResult:
    """Execute the full consolidation cycle (REM sleep).

    Strategies are applied in order:
        1. Cold purge (remove dead weight)
        2. Semantic merge (fuse near-duplicates)
        3. Diamond promotion (elevate high-impact)

    Args:
        db_conn: SQLite connection handle.
        vitals: Pre-assessed crystal vitals from thermometer.
        dry_run: If True, log actions but don't modify DB.

    Returns:
        ConsolidationResult with action counts.
    """
    result = ConsolidationResult(
        total_scanned=len(vitals),
        dry_run=dry_run,
    )

    logger.info(
        "🧹 [CONSOLIDATOR] Starting REM cycle%s — %d crystals to process",
        " (DRY RUN)" if dry_run else "",
        len(vitals),
    )

    if not vitals:
        return result

    # Strategy 1: Cold Purge
    await _execute_cold_purge(db_conn, vitals, result, dry_run)

    # Strategy 2: Semantic Merge (skip purged crystals)
    remaining = [v for v in vitals if v.recommendation != "PURGE"]
    await _execute_semantic_merge(db_conn, remaining, result, dry_run)

    # Strategy 3: Diamond Promotion
    await _execute_diamond_promotion(db_conn, remaining, result, dry_run)

    # Count skipped
    result.skipped = result.total_scanned - (result.purged + result.merged + result.promoted)

    logger.info(
        "🧹 [CONSOLIDATOR] REM cycle complete: purged=%d, merged=%d, "
        "promoted=%d, skipped=%d, errors=%d%s",
        result.purged,
        result.merged,
        result.promoted,
        result.skipped,
        result.errors,
        " (DRY RUN)" if dry_run else "",
    )

    return result
