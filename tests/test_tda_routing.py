
# [C5-REAL] Exergy-Maximized
"""
Tests for HodgeMemoryRouter in CORTEX memory routing.

Reality Level: C5-REAL
"""

import pytest
import sqlite3

from pathlib import Path
from cortex.utils.tda_routing import HodgeMemoryRouter




def test_memory_routing_discrete(tmp_path):
    # Setup a mock sqlite database to test the router locally
    db_file = tmp_path / "cortex_mock.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Create facts
    cursor.execute("""
    CREATE TABLE facts (
        id INTEGER PRIMARY KEY,
        project TEXT,
        content TEXT,
        exergy_score REAL,
        is_tombstoned INTEGER DEFAULT 0
    )
    """)

    # Create causal_edges
    cursor.execute("""
    CREATE TABLE causal_edges (
        id INTEGER PRIMARY KEY,
        fact_id INTEGER,
        parent_id INTEGER
    )
    """)

    # Insert facts
    # Node 1 -> Node 2 -> Node 3
    cursor.executemany(
        """
    INSERT INTO facts (id, project, content, exergy_score, is_tombstoned)
    VALUES (?, ?, ?, ?, ?)
    """,
        [
            (1, "Project Alpha", "Start fact", 1.0, 0),
            (2, "Project Alpha", "Middle fact", 1.5, 0),
            (3, "Project Alpha", "End fact", 2.0, 0),
        ],
    )

    # Insert edges (parent_id -> fact_id)
    cursor.executemany(
        """
    INSERT INTO causal_edges (fact_id, parent_id)
    VALUES (?, ?)
    """,
        [(2, 1), (3, 2)],
    )

    conn.commit()
    conn.close()

    router = HodgeMemoryRouter(db_path=db_file)
    nodes, edges = router.load_memory_graph()

    assert len(nodes) == 3
    assert len(edges[1]) == 1
    assert edges[1][0] == 2

    # Compute potential with Node 3 as target
    potential = router.compute_recall_potential(nodes, edges, target_ids=[3])

    # Node 3 should have highest potential (2.0)
    assert potential[3] == 2.0
    assert potential[2] > potential[1]

    # Geodesic descent path starting at 1
    path = router.geodesic_descent(start_id=1, potential=potential, edges=edges)
    assert path == [1, 2, 3]
