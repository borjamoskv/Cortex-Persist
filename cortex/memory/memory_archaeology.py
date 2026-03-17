"""
CORTEX v7 — Anamnesis-Ω Semantic Deduplicator (Memory Archaeology).

Finds isolated, isomorphic facts across the timeline and condenses them
into unified "crystallized" patterns. Transfers causal links (parent_decision_id).
"""

from __future__ import annotations

import logging
import sqlite3
import time
from typing import Any, Optional

import numpy as np

try:
    from cortex.extensions.llm.sovereign import SovereignLLM
except ImportError:
    SovereignLLM = None  # type: ignore[assignment, misc]

logger = logging.getLogger("cortex.memory.archaeology")


class MemoryArchaeologist:
    """Consolidates disjoint semantic facts into a single dense engram."""

    def __init__(self, engine: Any) -> None:
        self.engine = engine
        self.llm = SovereignLLM() if SovereignLLM else None

    async def run_archaeology(
        self, project: str, similarity_threshold: float = 0.88, simulate: bool = False
    ) -> dict[str, int]:
        """Runs the semantic clustering and deduction.

        Returns {"condensed": X, "tombstoned": Y}.
        """
        # Initialize memory subsystem (L2) explicitly before accessing
        await self.engine.get_conn()

        l3_map = self._fetch_active_facts(project)
        if not l3_map:
            return {"condensed": 0, "tombstoned": 0}

        facts, vecs_matrix = self._extract_vectors(project, l3_map)
        if vecs_matrix is None:
            return {"condensed": 0, "tombstoned": 0}

        clusters = self._build_clusters(facts, vecs_matrix, similarity_threshold)
        if not clusters:
            return {"condensed": 0, "tombstoned": 0}

        condensed, tombstoned = await self._synthesize_and_update(
            project, clusters, facts, simulate
        )
        return {"condensed": condensed, "tombstoned": tombstoned}

    def _fetch_active_facts(self, project: str) -> dict[str, dict[str, Any]]:
        conn = self.engine._get_sync_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, content, parent_decision_id
            FROM facts
            WHERE project = ? AND is_tombstoned = 0 AND fact_type != 'ghost'
            """,
            (project,),
        )
        # Using dict(r) to convert sqlite3.Row to dict
        return {str(r["id"]): dict(r) for r in cursor.fetchall()}

    def _extract_vectors(
        self, project: str, l3_map: dict[str, dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], Optional[np.ndarray]]:
        l2_conn = self.engine.memory._l2._get_conn()
        c2 = l2_conn.cursor()
        c2.execute(
            "SELECT m.id, v.embedding FROM facts_meta m JOIN vec_facts v ON m.rowid = v.rowid WHERE m.project_id = ?",
            (project,),
        )

        facts = []
        vecs = []
        for r in c2.fetchall():
            str_id = str(r["id"])
            if str_id not in l3_map:
                continue

            l3_rec = l3_map[str_id]
            facts.append(
                {
                    "id": str_id,
                    "content": l3_rec["content"],
                    "parent_decision_id": str(l3_rec["parent_decision_id"])
                    if l3_rec["parent_decision_id"]
                    else None,
                }
            )
            emb = np.frombuffer(r["embedding"], dtype=np.float32)
            # Normalize for cosine similarity
            norm = np.linalg.norm(emb)
            if norm > 0:
                emb = emb / norm
            vecs.append(emb)

        if not vecs:
            return facts, None

        return facts, np.vstack(vecs)

    def _build_clusters(
        self, facts: list[dict[str, Any]], vecs_matrix: np.ndarray, threshold: float
    ) -> list[list[int]]:
        # O(N^2) dot product for cosine similarity
        sim_matrix = np.dot(vecs_matrix, vecs_matrix.T)
        visited = set()
        clusters = []

        n = len(facts)
        for i in range(n):
            if i in visited:
                continue

            # Find neighbors
            neighbors = [j for j in range(n) if sim_matrix[i, j] >= threshold]
            if len(neighbors) > 1:
                clusters.append(neighbors)
                visited.update(neighbors)
            else:
                visited.add(i)

        return clusters

    async def _synthesize_and_update(
        self, project: str, clusters: list[list[int]], facts: list[dict[str, Any]], simulate: bool
    ) -> tuple[int, int]:
        condensed_count = 0
        tombstoned_count = 0
        conn = self.engine._get_sync_conn()
        l2_conn = self.engine.memory._l2._get_conn()

        for cluster_indices in clusters:
            if not self.llm:
                logger.warning("Archaeology bypassed: SovereignLLM is not installed.")
                continue

            cluster_facts = [facts[idx] for idx in cluster_indices]
            content_list = [f"- {f['content']}" for f in cluster_facts]
            prompt = (
                "You are an expert memory consolidator for CORTEX. "
                "Synthesize the following redundant facts into a single, dense, highly accurate 'Crystallized Pattern'. "
                "Retain all critical information, names, values, and relations, but remove redundancy.\n\n"
            ) + "\n".join(content_list)

            logger.info("Synthesizing cluster of size %s...", len(cluster_facts))
            res = await self.llm.agenerate(prompt)  # type: ignore[type-error]
            condensed_content = res.text.strip()

            parent_ids = [f["parent_decision_id"] for f in cluster_facts if f["parent_decision_id"]]
            primary_parent_id = parent_ids[0] if parent_ids else None
            old_ids = [f["id"] for f in cluster_facts]

            if not simulate:
                try:
                    await self._apply_db_updates(
                        project, condensed_content, old_ids, primary_parent_id, conn, l2_conn
                    )
                except sqlite3.Error as e:
                    logger.error("Archaeology DB update failed: %s", e)
                    continue

            condensed_count += 1
            tombstoned_count += len(cluster_facts)

        return condensed_count, tombstoned_count

    async def _apply_db_updates(
        self,
        project: str,
        condensed_content: str,
        old_ids: list[str],
        primary_parent_id: Optional[str],
        conn: sqlite3.Connection,
        l2_conn: sqlite3.Connection,
    ) -> None:
        # Prevent concurrent DB locks
        new_fact_id = await self.engine.store(
            project=project,
            content=condensed_content,
            fact_type="knowledge",
            confidence="C5",
            source="cortex_archaeologist",
            meta={"archaeology_merged_from": old_ids},
        )

        c3 = conn.cursor()
        placeholders = ",".join("?" for _ in old_ids)

        # Tombstone old ones
        c3.execute(
            f"UPDATE facts SET is_tombstoned = 1, valid_until = ? WHERE id IN ({placeholders})",
            [time.strftime("%Y-%m-%dT%H:%M:%S%z")] + old_ids,
        )

        if primary_parent_id:
            c3.execute(
                "UPDATE facts SET parent_decision_id = ? WHERE id = ?",
                (primary_parent_id, new_fact_id),
            )
            cl2 = l2_conn.cursor()
            cl2.execute(
                "UPDATE facts_meta SET parent_decision_id = ? WHERE id = ?",
                (primary_parent_id, new_fact_id),
            )

        # Delete tombstoned old ones from L2 to free up vector space
        cl2 = l2_conn.cursor()
        str_old_ids = [str(x) for x in old_ids]
        cl2.execute(f"DELETE FROM facts_meta WHERE id IN ({placeholders})", str_old_ids)
        cl2.execute("DELETE FROM vec_facts WHERE rowid NOT IN (SELECT rowid FROM facts_meta)")
        c3.execute(
            f"UPDATE facts SET parent_decision_id = ? WHERE parent_decision_id IN ({placeholders})",
            [new_fact_id] + old_ids,
        )
        cl2 = l2_conn.cursor()
        cl2.execute(
            f"UPDATE facts_meta SET parent_decision_id = ? WHERE parent_decision_id IN ({placeholders})",
            [new_fact_id] + old_ids,
        )

        conn.commit()
        l2_conn.commit()
