# [C5-REAL] Exergy-Maximized
"""
Ouroboros Hook.

Bridge between the swarm evolution engine (Ouroboros-∞) and the 
Tripartite Memory architecture (L1/L2/L3).
"""

from typing import Any

# Default 7 days
DEFAULT_MAX_AGE_SECONDS = 7 * 24 * 3600

async def get_dynamic_threshold(conn: Any, project: str) -> int:
    """
    [C5-REAL] Dynamic thermodynamic compaction threshold.
    Reads from the facts table or agent state to determine if Ouroboros 
    has overridden the compaction threshold due to high entropy.
    """
    try:
        # Check if there is an Ouroboros config fact overriding the threshold
        cursor = await conn.execute(
            """
            SELECT content FROM facts 
            WHERE project = ? AND fact_type = 'config' AND tags LIKE '%ouroboros_compaction_threshold%'
            ORDER BY valid_from DESC LIMIT 1
            """,
            (project,)
        )
        row = await cursor.fetchone()
        if row:
            import json
            data = json.loads(row[0])
            if "threshold_seconds" in data:
                return int(data["threshold_seconds"])
    except (ValueError, TypeError, OSError, KeyError):
        pass
    
    return DEFAULT_MAX_AGE_SECONDS
