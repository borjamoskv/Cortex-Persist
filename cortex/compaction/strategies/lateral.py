"""
Lateral inhibition strategy (C5 confirming over C3).
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.compaction.compactor import CompactionResult
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.compaction.lateral")
_LOG_FMT = "Compactor [%s] %s"


async def execute_lateral_inhibition(
    engine: "CortexEngine",
    project: str,
    result: "CompactionResult",
    dry_run: bool,
    similarity_threshold: float,
) -> None:
    """Execute the Lateral Inhibition strategy.

    Finds C5 facts, and if semantically colliding C3 (or lower) facts exist,
    the C3 facts are purged to eliminate asymptotic noise.
    """
    purged_ids = await _find_and_purge_colliding_c3s(engine, project, similarity_threshold, dry_run)
    if not purged_ids:
        return

    result.strategies_applied.append("lateral_inhibition")
    result.deprecated_ids.extend(purged_ids)

    detail = f"lateral_inhibition: purged {len(purged_ids)} noisy C3/lower facts."
    result.details.append(detail)
    logger.info(_LOG_FMT, project, detail)


async def _find_and_purge_colliding_c3s(
    engine: "CortexEngine",
    project: str,
    similarity_threshold: float,
    dry_run: bool,
) -> list[int]:
    """Find and purge C3 facts that collide with C5 facts."""
    conn = await engine.get_conn()
    purged_ids = []

    # 1. Encontrar todos los hechos C5 vigentes
    cursor = await conn.execute(
        "SELECT id, content FROM facts "
        "WHERE project = ? AND valid_until IS NULL AND confidence = 'C5'",
        (project,),
    )
    c5_rows = await cursor.fetchall()

    if not c5_rows:
        return []

    # Para cada hecho C5, buscamos colisiones con C3/lower usando sqlite-vec
    for c5_id, _ in c5_rows:
        # Recuperamos el embedding de este C5
        cursor = await conn.execute(
            "SELECT embedding FROM fact_embeddings WHERE fact_id = ?",
            (c5_id,),
        )
        v_row = await cursor.fetchone()

        if not v_row or not v_row[0]:
            continue

        c5_emb_bytes = v_row[0]

        # Buscamos nodos C3 o inferior semánticamente cercanos
        # En CORTEX las confidences menores suelen ser C3, C2, C1, inferred...
        # Excluimos C5 y C4 por seguridad. Focus en purga de ruido (C3 o inferred).
        target_confidences = ("C3", "C2", "C1", "inferred")
        marks = ",".join("?" for _ in target_confidences)

        # Ojo: la similitud mínima se gestiona filtrando la distancia.
        # similarity = 1.0 - (vec_distance_cosine / 2). Queremos similarity > threshold.
        # Por tanto, distance / 2 < 1.0 - threshold
        # distance < 2.0 * (1.0 - threshold)

        max_distance = 2.0 * (1.0 - similarity_threshold)

        cursor = await conn.execute(
            f"""
            SELECT f.id,
                   (1.0 - vec_distance_cosine(v.embedding, ?) / 2.0) as sim
            FROM facts f
            JOIN fact_embeddings v ON f.id = v.fact_id
            WHERE f.project = ?
              AND f.valid_until IS NULL
              AND f.confidence IN ({marks})
              AND vec_distance_cosine(v.embedding, ?) < ?
            """,
            (c5_emb_bytes, project, *target_confidences, c5_emb_bytes, max_distance),
        )
        colliding_rows = await cursor.fetchall()

        for c_id, sim in colliding_rows:
            if c_id not in purged_ids and c_id != c5_id:
                purged_ids.append(c_id)
                if not dry_run:
                    await engine.deprecate(
                        c_id, f"compacted:lateral_inhibition→#{c5_id} (sim={sim:.3f})"
                    )

    return purged_ids
