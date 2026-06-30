# [C5-REAL] Exergy-Maximized
# Author: Borja Moskv (borjamoskv)

from __future__ import annotations

import json
import logging
from typing import Any

import aiosqlite

from babylon60.crypto import get_default_encrypter
from babylon60.engine.mixins.base import FACT_COLUMNS, FACT_JOIN, EngineMixinBase
from babylon60.storage.classifier import (
    COMPOSITION_RULES,
    classify_content,
    detect_correlation_signals,
)

__all__ = ["PrivacyMixin"]

logger = logging.getLogger("cortex.privacy")


class PrivacyMixin(EngineMixinBase):
    """Zero-Trust Privacy Shield - Pre-storage Content Classification.

    Scans incoming content for sensitive patterns (API keys, private keys,
    connection strings) and injects audit metadata before persistence.
    Also performs Holistic Cross-Field Correlation Analysis (Composition Leakage Shield v7.0)
    against existing stored facts to prevent differential privacy correlation attacks.
    """

    async def _apply_privacy_shield(
        self,
        conn: aiosqlite.Connection,
        content: str,
        project: str,
        tenant_id: str,
        meta: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Zero-Trust Privacy Shield - classify content and analyze composition leakage before storage."""
        meta = meta or {}
        try:
            # 1. Static/Regex single-fact classification
            sensitivity = classify_content(content)
            if sensitivity.is_sensitive:
                logger.warning(
                    "PRIVACY SHIELD: Sensitive patterns detected (%s) in project [%s]. "
                    "Fact flagged for audit.",
                    ", ".join(sensitivity.matches),
                    project,
                )
                meta = {
                    **meta,
                    "privacy_flagged": True,
                    "privacy_matches": sensitivity.matches,
                    "privacy_score": sensitivity.score,
                }

            # 2. Holistic Cross-Field Correlation Analysis (Composition Leakage Shield v7.0)
            incoming_signals = detect_correlation_signals(content)
            if incoming_signals:
                logger.info(
                    "PRIVACY SHIELD: Correlation signals detected in incoming content (%s). "
                    "Analyzing holistic composition leakage against project facts...",
                    ", ".join(incoming_signals.keys()),
                )

                # Query the last 100 non-tombstoned facts for the same tenant and project
                query = f"SELECT {FACT_COLUMNS} {FACT_JOIN} WHERE f.tenant_id = ? AND f.project = ? AND f.is_tombstoned = 0 ORDER BY f.id DESC LIMIT 100"
                async with conn.execute(query, (tenant_id, project)) as cursor:
                    rows = await cursor.fetchall()

                enc = get_default_encrypter()
                flagged_stored_facts = []

                for row in rows:
                    fact_data = self._row_to_fact(row, tenant_id)
                    stored_content = fact_data.get("content", "")
                    stored_signals = detect_correlation_signals(stored_content)
                    if not stored_signals:
                        continue

                    # Evaluate composition rules on the union of signals
                    combined_keys = set(incoming_signals.keys()) | set(stored_signals.keys())
                    for rule_keys, category in COMPOSITION_RULES:
                        if rule_keys.issubset(combined_keys):
                            # Ensure we are not matching identical signals of the same value
                            triggered_keys = {
                                k
                                for k in rule_keys
                                if (k in incoming_signals and k not in stored_signals)
                                or (k in stored_signals and k not in incoming_signals)
                                or (incoming_signals.get(k) != stored_signals.get(k))
                            }
                            if len(triggered_keys) >= len(rule_keys) - 1:
                                logger.critical(
                                    "🚨 [PRIVACY SHIELD] Composition Leakage Detected (%s) "
                                    "between incoming content and stored Fact #%s.",
                                    category,
                                    fact_data["id"],
                                )
                                flagged_stored_facts.append((fact_data, category))
                                break

                if flagged_stored_facts:
                    # Update incoming fact metadata
                    correlated_ids = [f["id"] for f, _ in flagged_stored_facts]
                    meta = {
                        **meta,
                        "privacy_flagged": True,
                        "composition_leakage": True,
                        "composition_categories": list({c for _, c in flagged_stored_facts}),
                        "correlated_fact_ids": correlated_ids,
                        "privacy_score": max(meta.get("privacy_score", 0.0), 0.85),
                    }

                    # Retroactively update metadata of matched stored facts
                    from babylon60.database.core import causal_write

                    with causal_write(conn):
                        for stored_fact, category in flagged_stored_facts:
                            stored_id = stored_fact["id"]

                            async with conn.execute(
                                "SELECT metadata FROM facts WHERE id = ? AND tenant_id = ?",
                                (stored_id, tenant_id),
                            ) as c:
                                meta_row = await c.fetchone()

                            raw_meta = meta_row[0] if meta_row else None
                            stored_meta: dict[str, Any] = {}
                            is_encrypted = False

                            if raw_meta:
                                if isinstance(raw_meta, str) and raw_meta.startswith(enc.PREFIX):
                                    is_encrypted = True
                                    stored_meta = (
                                        enc.decrypt_json(raw_meta, tenant_id=tenant_id) or {}
                                    )
                                else:
                                    try:
                                        stored_meta = json.loads(raw_meta) or {}
                                    except Exception:
                                        stored_meta = {}

                            # Update stored metadata
                            stored_meta["privacy_flagged"] = True
                            stored_meta["composition_leakage"] = True
                            stored_meta["composition_category"] = category

                            updated_meta_json = json.dumps(stored_meta)
                            if is_encrypted:
                                updated_meta_json = enc.encrypt_json(
                                    stored_meta, tenant_id=tenant_id
                                )

                            await conn.execute(
                                "UPDATE facts SET metadata = ? WHERE id = ? AND tenant_id = ?",
                                (updated_meta_json, stored_id, tenant_id),
                            )

        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as exc:
            logger.warning("Suppressed exception: %s", exc)

        return meta
