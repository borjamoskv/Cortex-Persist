# [C5-REAL] Exergy-Maximized
"""
Anamnesis-Ω Semantic Deduplicator (Memory Archaeology).

Finds isolated, isomorphic facts across the timeline and condenses them
into unified "crystallized" patterns. Transfers causal links (parent_decision_id).
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from cortex.compat.optional import np  # lazy: pip install cortex-persist[compute]

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
        self,
        project: str,
        similarity_threshold: float = 0.88,
        simulate: bool = False,
        tenant_id: str | None = None,
    ) -> dict[str, int]:
        """Runs the semantic clustering and deduction.

        Returns {"condensed": X, "tombstoned": Y}.
        """
        # Initialize memory subsystem (L2) explicitly before accessing
        await self.engine.get_conn()
        tenant_id = self.engine._resolve_tenant(tenant_id or "default")

        l3_map = self._fetch_active_facts(project, tenant_id)  # pyright: ignore[reportArgumentType]
        if not l3_map:
            return {"condensed": 0, "tombstoned": 0}

        facts, vecs_matrix = self._extract_vectors(project, tenant_id, l3_map)  # pyright: ignore[reportArgumentType]
        if vecs_matrix is None:
            return {"condensed": 0, "tombstoned": 0}

        clusters = self._build_clusters(facts, vecs_matrix, similarity_threshold)
        if not clusters:
            return {"condensed": 0, "tombstoned": 0}

        condensed, tombstoned = await self._synthesize_and_update(
            project,
            tenant_id,  # type: ignore
            clusters,
            facts,
            simulate,  # pyright: ignore[reportArgumentType]
        )
        return {"condensed": condensed, "tombstoned": tombstoned}

    def _sync_parent_column(self, conn: sqlite3.Connection) -> str | None:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(facts)")
        columns = {str(row[1]) for row in cursor.fetchall()}
        if "parent_decision_id" in columns:
            return "parent_decision_id"
        if "parent_id" in columns:
            return "parent_id"
        return None

    def _fetch_active_facts(self, project: str, tenant_id: str) -> dict[str, dict[str, Any]]:
        conn = self.engine._get_sync_conn()
        cursor = conn.cursor()
        parent_col = self._sync_parent_column(conn)
        parent_col_select = (
            f", {parent_col} AS parent_decision_id"
            if parent_col
            else ", NULL AS parent_decision_id"
        )
        cursor.execute(
            f"""
            SELECT id, content{parent_col_select}, tenant_id
            FROM facts
            WHERE project = ? AND tenant_id = ? AND is_tombstoned = 0 AND fact_type != 'ghost'
            """,
            (project, tenant_id),
        )
        # Using dict(r) to convert sqlite3.Row to dict
        return {str(r["id"]): dict(r) for r in cursor.fetchall()}

    def _extract_vectors(
        self, project: str, tenant_id: str, l3_map: dict[str, dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], np.ndarray | None]:  # pyright: ignore[reportInvalidTypeForm]
        l2_conn = self.engine.memory._l2._get_conn()
        c2 = l2_conn.cursor()
        c2.execute(
            "SELECT m.id, v.embedding FROM facts_meta m JOIN vec_facts v ON m.rowid = v.rowid "
            "WHERE m.project_id = ? AND m.tenant_id = ?",
            (project, tenant_id),
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
                    "tenant_id": l3_rec.get("tenant_id") or "default",
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
        self,
        facts: list[dict[str, Any]],
        vecs_matrix: np.ndarray,  # type: ignore
        threshold: float,  # pyright: ignore[reportInvalidTypeForm]
    ) -> list[list[int]]:
        # O(N^2) dot product for cosine similarity is unavoidable here without approximate KNN.
        # But we can eliminate the O(N^2) nested python loops and use vectorization.
        sim_matrix = np.dot(vecs_matrix, vecs_matrix.T)

        # Zero out the diagonal to not match with self during boolean indexing
        np.fill_diagonal(sim_matrix, 0)

        # Find all pairs above threshold
        matches = sim_matrix >= threshold

        visited = set()
        clusters = []
        n = len(facts)

        for i in range(n):
            if i in visited:
                continue

            # Get indices where the match is true
            neighbors = np.where(matches[i])[0].tolist()

            # Since diagonal is zeroed out, we need to explicitly add `i` if it has neighbors
            if neighbors:
                cluster = [i] + neighbors
                clusters.append(cluster)
                visited.update(cluster)
            else:
                visited.add(i)

        return clusters

    async def _synthesize_and_update(
        self,
        project: str,
        tenant_id: str,
        clusters: list[list[int]],
        facts: list[dict[str, Any]],
        simulate: bool,
    ) -> tuple[int, int]:
        condensed_count = 0
        tombstoned_count = 0
        l2_conn = self.engine.memory._l2._get_conn()

        for cluster_indices in clusters:
            if not self.llm:
                logger.warning("Archaeology bypassed: SovereignLLM is not installed.")
                continue

            cluster_facts = [facts[idx] for idx in cluster_indices]
            if any(str(f.get("tenant_id") or "default") != tenant_id for f in cluster_facts):
                raise ValueError("Archaeology cluster spans multiple tenants")

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
            [f["id"] for f in cluster_facts]

            if not simulate:
                try:
                    await self._apply_db_updates(
                        project,
                        tenant_id,
                        condensed_content,
                        cluster_facts,
                        primary_parent_id,
                        l2_conn,
                    )
                except (sqlite3.Error, aiosqlite.Error) as e:
                    logger.error("Archaeology DB update failed: %s", e)
                    continue

            condensed_count += 1
            tombstoned_count += len(cluster_facts)

        return condensed_count, tombstoned_count

    async def _apply_db_updates(
        self,
        project: str,
        tenant_id: str,
        condensed_content: str,
        cluster_facts: list[dict[str, Any]],
        primary_parent_id: str | None,
        l2_conn: sqlite3.Connection,
    ) -> None:
        from cortex.engine.core.mutation_engine import MUTATION_ENGINE

        old_ids = [str(f["id"]) for f in cluster_facts]
        ts = datetime.now(timezone.utc).isoformat()
        new_fact_id = await self.engine.store(
            project=project,
            tenant_id=tenant_id,
            content=condensed_content,
            fact_type="knowledge",
            confidence="C5",
            source="cortex_archaeologist",
            meta={"archaeology_merged_from": old_ids},
            parent_decision_id=int(primary_parent_id) if primary_parent_id else None,
        )

        placeholders = ",".join("?" for _ in old_ids)
        async with self.engine.session() as conn:
            for fact in cluster_facts:
                await MUTATION_ENGINE.apply(
                    conn,
                    fact_id=int(fact["id"]),
                    tenant_id=str(fact.get("tenant_id") or "default"),
                    event_type="archaeology_merge",
                    payload={
                        "timestamp": ts,
                        "reason": "archaeology-merged",
                        "replacement_fact_id": new_fact_id,
                    },
                    signer="memory.archaeology",
                    commit=False,
                )

            parent_column = await self._parent_column(conn)
            if parent_column:
                cursor = await conn.execute(
                    f"SELECT id, tenant_id FROM facts "  # nosec B608
                    f"WHERE {parent_column} IN ({placeholders}) AND tenant_id = ?",  # nosec B608
                    (*old_ids, tenant_id),
                )
                for child_id, child_tenant_id in await cursor.fetchall():
                    if str(child_id) in old_ids:
                        continue
                    await MUTATION_ENGINE.apply(
                        conn,
                        fact_id=int(child_id),
                        tenant_id=str(child_tenant_id or "default"),
                        event_type="reparent",
                        payload={"parent_decision_id": new_fact_id, "timestamp": ts},
                        signer="memory.archaeology",
                        commit=False,
                    )
            await conn.commit()

        # Delete tombstoned old ones from L2 to free up vector space
        cl2 = l2_conn.cursor()
        str_old_ids = [str(x) for x in old_ids]
        if primary_parent_id:
            cl2.execute(
                "UPDATE facts_meta SET parent_decision_id = ? WHERE id = ?",
                (primary_parent_id, new_fact_id),
            )
            
        try:
            from cortex.engine.core.l3_archive import l3_archiver
            l3_archiver.archive_facts(cluster_facts)
        except Exception as e:
            import logging
            logging.getLogger("cortex.memory.archaeology").warning("L3 Archival failed: %s", e)
            
        cl2.execute(f"DELETE FROM facts_meta WHERE id IN ({placeholders})", str_old_ids)  # nosec B608
        cl2.execute("DELETE FROM vec_facts WHERE rowid NOT IN (SELECT rowid FROM facts_meta)")
        cl2 = l2_conn.cursor()
        cl2.execute(
            f"UPDATE facts_meta SET parent_decision_id = ? WHERE parent_decision_id IN ({placeholders})",  # nosec B608
            [new_fact_id] + old_ids,
        )
        l2_conn.commit()

    async def _parent_column(self, conn: aiosqlite.Connection) -> str | None:
        cursor = await conn.execute("PRAGMA table_info(facts)")
        columns = {str(row[1]) for row in await cursor.fetchall()}
        if "parent_decision_id" in columns:
            return "parent_decision_id"
        if "parent_id" in columns:
            return "parent_id"
        return None
