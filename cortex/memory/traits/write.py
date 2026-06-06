# [C5-REAL] Exergy-Maximized
import asyncio
import json
import logging
import sqlite3

from cortex.compat.optional import np
from cortex.guards.exergy_guard import calculate_exergy
from cortex.memory.models import CortexFactModel
from cortex.utils import void_vec

logger = logging.getLogger(__name__)


class WriteTrait:
    async def memorize(self, fact: CortexFactModel) -> None:
        """Encode and store a multi-tenant CortexFactModel.

        Applies PII sanitization to content before storage if a sanitizer
        is available. The sanitized content is stored and vectorized;
        encrypted PII fragments are persisted in the metadata field.
        """
        conn = self._get_conn()  # pyright: ignore[reportAttributeAccessIssue]
        from cortex.engine.causal.taint_engine import enforce_taint_check

        token = fact.metadata.get("cortex_taint") if fact.metadata else None
        await enforce_taint_check(conn, token, fact.content)

        # ─── PII Sanitization Gate (Moved outside the DB Lock) ────────
        sanitized_content = fact.content
        sanitized_meta = dict(fact.metadata) if fact.metadata else {}

        sanitizer = self._get_sanitizer()  # pyright: ignore[reportAttributeAccessIssue]
        if sanitizer and fact.content:
            report = await asyncio.to_thread(
                sanitizer.sanitize, fact.content, tenant_id=fact.tenant_id
            )
            if report.has_pii:
                sanitized_content = report.sanitized
                if report.encrypted_fragments:
                    sanitized_meta["_pii_fragments"] = report.encrypted_fragments
                    sanitized_meta["_pii_categories"] = [c.value for c in report.pii_categories]

        def _offloaded_computations() -> tuple[bytes, bytes, float]:
            ex = calculate_exergy(sanitized_content)
            emb_list = fact.embedding
            if isinstance(emb_list, bytes):
                # Cannot easily dual-quantize from raw bytes without knowing source
                return emb_list, b"", ex

            arr = np.array(emb_list, dtype=np.float32)
            int8_bytes = arr.tobytes()
            binary_bytes = void_vec.pack_void_bit(arr)
            return int8_bytes, binary_bytes, ex

        int8_bytes, binary_bytes, exergy_val = await asyncio.to_thread(_offloaded_computations)

        def _sync_insert() -> None:
            cursor = conn.cursor()
            try:
                meta_tb, vec_tb, vec_void_tb, mih_tb = self._get_domain_tables(  # pyright: ignore[reportAttributeAccessIssue]
                    conn, fact.tenant_id, fact.project_id
                )
                insert_meta_sql = f"""
                    INSERT INTO {meta_tb} (
                        id, tenant_id, project_id, content, timestamp,
                        is_diamond, is_bridge, confidence, success_rate,
                        cognitive_layer, parent_decision_id, metadata, exergy_score,
                        category, quadrant, storage_tier, facet_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                cursor.execute(
                    insert_meta_sql,
                    (
                        fact.id,
                        fact.tenant_id,
                        fact.project_id,
                        sanitized_content,
                        fact.timestamp,
                        int(fact.is_diamond),
                        int(fact.is_bridge),
                        fact.confidence,
                        fact.success_rate,
                        fact.cognitive_layer,
                        fact.parent_decision_id,
                        json.dumps(sanitized_meta),
                        exergy_val,
                        fact.category,
                        fact.quadrant,
                        fact.storage_tier,
                        fact.facet_version,
                    ),
                )
                rowid = cursor.lastrowid
                if self._vector_enabled:  # pyright: ignore[reportAttributeAccessIssue]
                    # Store 1-bit Vector (Legion Recall)
                    if vec_void_tb:
                        insert_void_sql = (
                            f"INSERT INTO {vec_void_tb}(rowid, embedding) VALUES (?, ?)"
                        )
                        cursor.execute(
                            insert_void_sql,
                            (rowid, binary_bytes),
                        )
                        # MIH Indexing
                        from cortex.utils.void_mih import slice_void_bit

                        shards = slice_void_bit(binary_bytes)
                        insert_mih_sql = (
                            f"INSERT INTO {mih_tb} (rowid, s0, s1, s2, s3, s4, s5, s6, s7, s8, s9, "
                            "s10, s11, s12, s13, s14, s15) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                        )
                        cursor.execute(
                            insert_mih_sql,
                            (rowid, *shards),
                        )

                    # Store int8 Vector (HdrRecovery Reranking)
                    # Only skip if tier is explicitly COLD to save space
                    if fact.storage_tier != "COLD" and vec_tb:
                        insert_int8_sql = (
                            f"INSERT INTO {vec_tb}(rowid, embedding) "
                            "VALUES (?, vec_quantize_int8(?, 'unit'))"
                        )
                        cursor.execute(
                            insert_int8_sql,
                            (rowid, int8_bytes),
                        )
                conn.commit()
            except (sqlite3.Error, RuntimeError) as e:
                conn.rollback()
                logger.error("DB integrity breach during memorize: %s", e)
                raise

        async with self._lock:  # pyright: ignore[reportAttributeAccessIssue]
            await asyncio.to_thread(_sync_insert)
