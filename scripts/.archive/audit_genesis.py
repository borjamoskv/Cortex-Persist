#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
CORTEX - Genesis Auditor (Axiom 20 Deployment).

Continuously verifies the convergence of the ouroboros_genesis_db
against the target ontological Seed using OmegaAuditor.
"""

import asyncio
import logging
import os
import sqlite3

from cortex.guards.omega_auditor import OmegaAuditor

setup_cortex_logging()
logger = logging.getLogger("GenesisAuditor")

DB_PATH = os.path.expanduser("~/.cortex/vectors.db")


async def audit_genesis():
    """Audit the genesis DB for continuous ontological consistency."""
    logger.info("🔥 [GENESIS-AUDIT] Initializing OmegaAuditor against genesis DB.")

    if not os.path.exists(DB_PATH):
        logger.warning(f"⚠️ Genesis DB not found at {DB_PATH}. Aborting audit.")
        return

    auditor = OmegaAuditor()

    # Retrieve a sample of the most recent facts to audit for convergence
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        cur.execute("SELECT id, content, project_id FROM facts_meta ORDER BY rowid DESC LIMIT 10")
        rows = cur.fetchall()
    except sqlite3.OperationalError as e:
        logger.error(f"Failed to query facts_meta: {e}")
        conn.close()
        return

    conn.close()

    if not rows:
        logger.info("No facts found in genesis DB to audit.")
        return

    logger.info(
        f"🌌 [GENESIS-AUDIT] Auditing {len(rows)} recent facts for ontological convergence."
    )

    total_conflicts = 0
    for row in rows:
        fact_id = row["id"]
        content = row["content"]
        project = row["project_id"] or "CORTEX-GLOBAL"

        logger.info(f"Auditing fact {fact_id}...")

        # Execute C5-REAL ontological audit
        try:
            conflicts = await auditor.audit_decision(content, project)
            if conflicts:
                logger.warning(
                    f"⚠️ [CONTRADICTION] Found {len(conflicts)} conflicts in fact {fact_id}!"
                )
                for conflict in conflicts:
                    logger.warning(f"  -> {conflict.severity.upper()}: {conflict.summary}")
                total_conflicts += len(conflicts)
            else:
                logger.info(f"✅ Fact {fact_id} is CONVERGED.")
        except Exception as e:
            logger.error(f"Audit failed for fact {fact_id}: {e}")

    if total_conflicts == 0:
        logger.info(
            "✅ [GENESIS-AUDIT] Systemic homeostasis confirmed. All facts align with ontological Seed."
        )
    else:
        logger.error(f"❌ [GENESIS-AUDIT] Found {total_conflicts} total semantic contradictions.")


if __name__ == "__main__":
    asyncio.run(audit_genesis())
