# [C5-REAL] Exergy-Maximized
import asyncio
import json
import sqlite3
import time
from typing import Any

from babylon60.compat.optional import np
from babylon60.memory.models import CortexFactModel, SourceMetadata
from babylon60.utils import void_vec
from babylon60.utils.turboquant import encode_query_qjl


class ReadTrait:
    async def recall_secure(
        self,
        tenant_id: str,
        project_id: str,
        query: str,
        limit: int = 5,
        layer: str | None = None,
    ) -> list[CortexFactModel]:
        """[C5] Recuperación particionada Zero-Trust con ranking SQL nativo."""
        conn = self._get_conn()  # pyright: ignore[reportAttributeAccessIssue]
        query_vector = await self._encoder.encode(query)  # pyright: ignore[reportAttributeAccessIssue]

        def _sync_knn_search() -> list[CortexFactModel]:
            rotated_query = encode_query_qjl(query_vector)
            embedding_bytes = np.array(rotated_query, dtype=np.float32).tobytes()
            void_query = void_vec.pack_void_bit(rotated_query)
            now = time.monotonic()

            cursor = conn.cursor()
            meta_tb, vec_tb, vec_void_tb, mih_tb = self._get_domain_tables(  # pyright: ignore[reportAttributeAccessIssue]
                conn, tenant_id, project_id
            )

            if not self._vector_enabled:  # pyright: ignore[reportAttributeAccessIssue]
                sql = (
                    f"SELECT * FROM {meta_tb} "
                    "WHERE tenant_id = ? AND (project_id = ? OR is_bridge = 1)"
                )
                params: list[Any] = [tenant_id, project_id]
                if layer:
                    sql += " AND cognitive_layer = ?"
                    params.append(layer)
                sql += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)

                cursor.execute(sql, tuple(params))
                rows = cursor.fetchall()
                final_facts = []
                for row in rows:
                    parsed_meta = json.loads(row["metadata"]) if row["metadata"] else {}
                    source_meta_dict = parsed_meta.get("source_metadata")
                    if source_meta_dict:
                        try:
                            source_meta = SourceMetadata.model_validate(source_meta_dict)
                        except Exception:
                            source_meta = SourceMetadata(origin="system", author="unknown", confidence_in_source=1.0)
                    else:
                        source_meta = SourceMetadata(origin="system", author="unknown", confidence_in_source=1.0)
                    fact = CortexFactModel(
                        id=row["id"],
                        tenant_id=row["tenant_id"],
                        project_id=row["project_id"],
                        content=row["content"],
                        embedding=[],
                        timestamp=row["timestamp"],
                        is_diamond=bool(row["is_diamond"]),
                        is_bridge=bool(row["is_bridge"]),
                        confidence=row["confidence"],
                        cognitive_layer=row["cognitive_layer"],
                        parent_decision_id=row["parent_decision_id"],
                        source_metadata=source_meta,
                        metadata=parsed_meta,
                    )
                    object.__setattr__(fact, "_recall_score", 0.0)
                    final_facts.append(fact)
                return final_facts

            use_void = False
            if vec_void_tb:
                try:
                    count_void_sql = f"SELECT count(1) FROM {vec_void_tb}"
                    cursor.execute(count_void_sql)
                    row = cursor.fetchone()
                    use_void = (row[0] > 0) if row else False
                except sqlite3.OperationalError:
                    use_void = False

            if use_void:
                from babylon60.utils.void_mih import slice_void_bit

                q_shards = slice_void_bit(void_query)

                meta_tb, vec_tb, vec_void_tb, mih_tb = self._get_domain_tables(  # pyright: ignore[reportAttributeAccessIssue]
                    conn, tenant_id, project_id
                )

                # Candidate criteria: at least 1 shard match (1/16)
                where_mih = " OR ".join([f"s{i} = ?" for i in range(16)])

                # VOID-QUANT v2: Fetch candidate pool via Hamming, rerank in SQL (HdrRecovery + Decay)
                sql_cand = f"""
                    WITH candidates AS (
                        SELECT rowid FROM {mih_tb}
                        WHERE {where_mih}
                        LIMIT ?
                    )
                    SELECT * FROM (
                        SELECT m.*, v.embedding as binary_emb,
                               coalesce(
                                   (1.0 - vec_distance_cosine(vf.embedding,
                                          vec_quantize_int8(?, 'unit')) / 2.0),
                                   (1.0 - (void_dist(?, v.embedding) / CAST(? AS REAL)))
                               ) as base_similarity,
                               (
                                   coalesce(
                                       (1.0 - vec_distance_cosine(vf.embedding,
                                              vec_quantize_int8(?, 'unit')) / 2.0),
                                       (1.0 - (void_dist(?, v.embedding) / CAST(? AS REAL)))
                                   ) *
                                   cortex_decay(m.is_diamond, m.timestamp, ?, ?) *
                                   m.success_rate * m.exergy_score
                               ) as final_score
                        FROM {meta_tb} m
                        JOIN {vec_void_tb} v ON m.rowid = v.rowid
                        LEFT JOIN {vec_tb} vf ON m.rowid = vf.rowid
                        JOIN candidates c ON m.rowid = c.rowid
                        WHERE m.tenant_id = ? AND (m.project_id = ? OR m.is_bridge = 1)
                    ) WHERE base_similarity > 0.3
                    ORDER BY final_score DESC LIMIT ?
                """
                params_cand = [
                    *q_shards,
                    int(limit * 10),  # limit for candidates
                    embedding_bytes,
                    void_query,
                    int(self._encoder.dimension),  # pyright: ignore[reportAttributeAccessIssue]
                    embedding_bytes,
                    void_query,
                    int(self._encoder.dimension),  # pyright: ignore[reportAttributeAccessIssue]
                    float(now),
                    float(self._half_life),  # pyright: ignore[reportAttributeAccessIssue]
                    str(tenant_id),
                    str(project_id),
                    int(limit),
                ]
                cursor.execute(sql_cand, tuple(params_cand))
                rows = cursor.fetchall()

            else:
                # [KEEP ORIGINAL Non-Void Path for int8 vectors]
                sql = f"""
                    SELECT * FROM (
                        SELECT
                            m.*, v.embedding as binary_emb,
                            (1.0 - vec_distance_cosine(v.embedding,
                                     vec_quantize_int8(?, 'unit')) / 2.0) as base_similarity,
                            ((1.0 - vec_distance_cosine(v.embedding,
                                       vec_quantize_int8(?, 'unit')) / 2.0) *
                             cortex_decay(m.is_diamond, m.timestamp, ?, ?) *
                             m.success_rate * m.exergy_score) as final_score
                        FROM {meta_tb} m
                        JOIN {vec_tb} v ON m.rowid = v.rowid
                        WHERE m.tenant_id = ? AND (m.project_id = ? OR m.is_bridge = 1)
                    ) WHERE base_similarity > 0.3
                    ORDER BY final_score DESC LIMIT ?
                """
                params_vec = [
                    embedding_bytes,
                    embedding_bytes,
                    float(now),
                    float(self._half_life),  # pyright: ignore[reportAttributeAccessIssue]
                    str(tenant_id),
                    str(project_id),
                    int(limit),
                ]
                cursor.execute(sql, tuple(params_vec))
                rows = cursor.fetchall()

            if not rows:
                return []

            final_facts = []
            for row in rows:
                parsed_meta = json.loads(row["metadata"]) if row["metadata"] else {}
                source_meta_dict = parsed_meta.get("source_metadata")
                if source_meta_dict:
                    try:
                        source_meta = SourceMetadata.model_validate(source_meta_dict)
                    except Exception:
                        source_meta = SourceMetadata(origin="system", author="unknown", confidence_in_source=1.0)
                else:
                    source_meta = SourceMetadata(origin="system", author="unknown", confidence_in_source=1.0)
                fact = CortexFactModel(
                    id=row["id"],
                    tenant_id=row["tenant_id"],
                    project_id=row["project_id"],
                    content=row["content"],
                    embedding=row["binary_emb"],
                    timestamp=row["timestamp"],
                    is_diamond=bool(row["is_diamond"]),
                    is_bridge=bool(row["is_bridge"]),
                    confidence=row["confidence"],
                    cognitive_layer=row["cognitive_layer"],
                    parent_decision_id=row["parent_decision_id"],
                    source_metadata=source_meta,
                    metadata=parsed_meta,
                )
                object.__setattr__(fact, "_recall_score", row["final_score"])
                final_facts.append(fact)
            return final_facts

        return await asyncio.to_thread(_sync_knn_search)

    async def recall(
        self, query: str, limit: int = 5, project: str | None = None, tenant_id: str = "default"
    ) -> list[CortexFactModel]:
        """Backward-compatible recall for legacy callers. Maps to recall_secure."""
        return await self.recall_secure(
            tenant_id=tenant_id, project_id=project or "default", query=query, limit=limit
        )

    async def recall_hybrid(
        self,
        query: str,
        query_embedding: list[float],
        tenant_id: str = "default",
        project_id: str = "default",
        limit: int = 5,
        vector_weight: float = 0.6,
        text_weight: float = 0.4,
    ):
        """L2 Hybrid Search: Vector KNN + FTS5 BM25 fused via RRF."""
        if self._hybrid is not None:  # pyright: ignore[reportAttributeAccessIssue]
            return await self._hybrid.search(  # pyright: ignore[reportAttributeAccessIssue]
                query=query,
                query_embedding=query_embedding,
                tenant_id=tenant_id,
                project_id=project_id,
                top_k=limit,
                vector_weight=vector_weight,
                text_weight=text_weight,
            )
        return await self.recall_secure(
            tenant_id=tenant_id, project_id=project_id, query=query, limit=limit
        )
