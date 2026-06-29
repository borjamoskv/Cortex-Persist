# [C5-REAL] Exergy-Maximized
"""
COGNITIVE-DB: Database migration and schema ensure logic.
"""

from __future__ import annotations

import logging
from typing import Any

from babylon60.audit.cognitive_config import _CREATE_ROUTER_LOG_SQL
from babylon60.crypto.hash_registry import cortex_hash

logger = logging.getLogger("cortex.audit.cognitive_db")


async def ensure_table_for_router(router: Any) -> None:
    """Ensures log table existence and migrates old schemas to support unique constraints."""
    if router._ready:
        return
    async with router._lock:
        if router._ready:
            return

        cursor = await router._conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='cognitive_router_log'"
        )
        row = await cursor.fetchone()
        if row:
            sql = row[0]
            if (
                "UNIQUE" not in sql
                or "classifier_version" not in sql
                or "routing_policy_version" not in sql
            ):
                from babylon60.database.core import causal_write

                try:
                    with causal_write(router._conn):
                        await router._conn.execute(
                            "ALTER TABLE cognitive_router_log RENAME TO _cognitive_router_log_old"
                        )
                        await router._conn.execute(_CREATE_ROUTER_LOG_SQL)

                        cursor_old = await router._conn.execute(
                            "PRAGMA table_info(_cognitive_router_log_old)"
                        )
                        old_cols = [r[1] for r in await cursor_old.fetchall()]

                        select_cols = [
                            "routing_id",
                            "timestamp",
                            "prompt_hash",
                            "detected_sensitivity",
                            "user_tier",
                            "assigned_model",
                            "data_retention_flag",
                            "prev_hash",
                            "signature",
                        ]
                        insert_cols = list(select_cols)

                        if "classifier_version" in old_cols:
                            select_cols.append("classifier_version")
                            insert_cols.append("classifier_version")
                        else:
                            select_cols.append(f"'{router.classifier.version}'")
                            insert_cols.append("classifier_version")

                        if "routing_policy_version" in old_cols:
                            select_cols.append("routing_policy_version")
                            insert_cols.append("routing_policy_version")
                        else:
                            select_cols.append(f"'{router.routing_policy['version']}'")
                            insert_cols.append("routing_policy_version")

                        query = f"INSERT INTO cognitive_router_log ({', '.join(insert_cols)}) SELECT {', '.join(select_cols)} FROM _cognitive_router_log_old"
                        await router._conn.execute(query)
                        await router._conn.execute("DROP TABLE _cognitive_router_log_old")
                        await router._conn.commit()
                except Exception as e:
                    logger.error("Failed to migrate cognitive_router_log table: %s", e)
                    raise
        else:
            from babylon60.database.core import causal_write

            with causal_write(router._conn):
                await router._conn.execute(_CREATE_ROUTER_LOG_SQL)
                await router._conn.commit()

        cursor = await router._conn.execute(
            "SELECT timestamp, prompt_hash, detected_sensitivity, user_tier, assigned_model, data_retention_flag, prev_hash, classifier_version, routing_policy_version FROM cognitive_router_log ORDER BY rowid DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        if row:
            (
                timestamp,
                prompt_hash,
                sensitivity_json,
                user_tier,
                assigned_model,
                retention_flag,
                prev_hash,
                classifier_ver,
                routing_policy_ver,
            ) = row

            payload_obj = {
                "timestamp": timestamp,
                "prompt_hash": prompt_hash,
                "detected_sensitivity": sensitivity_json,
                "user_tier": user_tier,
                "assigned_model": assigned_model,
                "data_retention_flag": retention_flag,
                "prev_hash": prev_hash,
                "classifier_version": classifier_ver,
                "routing_policy_version": routing_policy_ver,
            }
            payload_bytes = router.canonical_json(payload_obj)
            router._last_hash = cortex_hash(payload_bytes)
        else:
            router._last_hash = "GENESIS"
        router._ready = True
