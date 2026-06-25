# [C5-REAL] Exergy-Maximized
"""
Neural Hive API.

Endpoints for visualizing the memory graph in 3D.
"""

import sqlite3

# --- C5-REAL BFT PATCH (R10) ---
import sqlite3 as _sqlite3_bft_orig
_orig_sqlite_connect = _sqlite3_bft_orig.connect
def _bft_sqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    conn = _orig_sqlite_connect(*args, **kwargs)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn
_sqlite3_bft_orig.connect = _bft_sqlite_connect
# -------------------------------

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from legacy_research.auth import AuthResult, require_permission

__all__ = [
    "GraphData",
    "GraphLink",
    "GraphNode",
    "get_hive_graph",
]

router = APIRouter(prefix="/hive", tags=["hive"])


class GraphNode(BaseModel):
    id: int
    val: int  # size/relevance
    name: str  # content snippet
    group: str  # project or type
    color: str


class GraphLink(BaseModel):
    source: int
    target: int
    value: float  # distance/similarity


class GraphData(BaseModel):
    nodes: list[GraphNode]
    links: list[GraphLink]


@router.get("/graph", response_model=GraphData)
def get_hive_graph(
    limit: int = 500,
    auth: AuthResult = Depends(require_permission("read")),
):
    """
    Get the knowledge graph for 3D visualization.
    Nodes are facts, links are semantic similarities.
    """
    from legacy_research.config import DB_PATH
    from legacy_research.database.core import connect

    conn = connect(DB_PATH, row_factory=sqlite3.Row)

    try:
        # 1. Fetch recent/important nodes
        cursor = conn.execute(
            """
            SELECT id, content, project, fact_type, created_at
            FROM facts
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()

        nodes = []
        node_ids = set()

        project_colors = {
            "cortex": "#00ff88",  # Cyber Green
            "naroa": "#ff0088",  # Cyber Pink
            "system": "#0088ff",  # Cyber Blue
        }
        default_color = "#ffffff"

        for row in rows:
            nid = row["id"]
            node_ids.add(nid)
            project = row["project"] or "system"

            nodes.append(
                GraphNode(
                    id=nid,
                    val=1,
                    name=row["content"][:50] + "...",
                    group=project,
                    color=project_colors.get(project.lower(), default_color),
                )
            )

        # 2. Fetch edges (semantic connections)
        # using vec_distance if available, or just random/temporal for now if no embeddings
        # For this MVP, we will try to get connections from embeddings if possible.

        links = []

        # Check if vectors exist
        try:
            vec_cursor = conn.execute("SELECT count(*) FROM fact_embeddings")
            has_vecs = vec_cursor.fetchone()[0] > 0
        except sqlite3.Error:
            has_vecs = False

        if has_vecs:
            # Slow O(N^2) approach for MVP or use sqlite-vec knn on a subset
            # Let's just link sequential items for now to ensure visualization works
            # Real implementation needs optimized KNN query

            # Simple temporal links for MVP 1.0
            prev_id = None
            for node in nodes:
                if prev_id:
                    links.append(GraphLink(source=prev_id, target=node.id, value=1.0))
                prev_id = node.id

        return GraphData(nodes=nodes, links=links)

    except (sqlite3.Error, OSError, RuntimeError) as e:
        raise HTTPException(status_code=500, detail=str(e)) from None
    finally:
        conn.close()
