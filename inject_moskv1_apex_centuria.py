#!/usr/bin/env python3
"""
inject_moskv1_apex_centuria.py
═══════════════════════════════════════════════════════════════
Inyección de APEX-051→APEX-100 (Centuria Expansion)
FASE 6: Operaciones Ofensivas (051-075)
FASE 7: Síntesis Filosófica y Metacognición (076-100)
═══════════════════════════════════════════════════════════════
Protocolo: C5-REAL | Autor: borjamoskv
"""

import asyncio
import logging
import os
import re
import sys

sys.path.insert(0, os.path.abspath('.'))

from cortex.audit.ledger import EnterpriseAuditLedger
from cortex.engine.autodidact_hott_engine import AutodidactHottEngine
from cortex.engine.ultramap import UltramapSubstrate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("inject_moskv1_apex_centuria")

# Only inject APEX-051 through APEX-100
RANGE_START = 51
RANGE_END = 100


async def inject_centuria():
    logger.info(
        f"Iniciando inyección de APEX-{RANGE_START:03d}→APEX-{RANGE_END:03d} "
        f"(Centuria Expansion — {RANGE_END - RANGE_START + 1} primitivas)..."
    )

    ultramap = UltramapSubstrate(capacity=10000)
    ledger = EnterpriseAuditLedger(
        log_path=os.getenv("CORTEX_LOG_PATH", "security_audit_log.jsonl"),
    )
    hott_engine = AutodidactHottEngine(ledger=ledger, ultramap=ultramap)

    md_path = "AUTODIDACT_MOSKV1_APEX_CAPABILITIES.md"
    with open(md_path, encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(r'-\s*\*\*(APEX-(\d{3}))\*\*:\s*`?([^`\n]+?)`?\s*-\s*(.*)')
    all_matches = pattern.findall(content)

    # Filter to only new primitives
    new_matches = [
        m for m in all_matches
        if RANGE_START <= int(m[1]) <= RANGE_END
    ]

    logger.info(
        f"Primitivas totales en MD: {len(all_matches)} | "
        f"Nuevas a inyectar: {len(new_matches)}"
    )

    if len(new_matches) != (RANGE_END - RANGE_START + 1):
        logger.warning(
            f"Esperadas {RANGE_END - RANGE_START + 1} primitivas, "
            f"encontradas {len(new_matches)}. Continuando con las disponibles."
        )

    agent_id = 99
    ultramap.update_agent_position(
        agent_id, 50.0, 0.0, 0.0, "MOSKV1_APEX_CENTURIA_ROOT", 0.0,
    )

    success_count = 0
    fail_count = 0
    total = len(new_matches)

    for i, match in enumerate(new_matches):
        p_id = match[0].strip()       # APEX-0XX
        p_num = int(match[1])          # numeric index
        p_name = match[2].strip()      # capability name
        p_app = match[3].strip()       # description

        axiom_claim = f"{p_id}: {p_name}"
        constructive_proof = (
            f"Aplicación estructural en C5-REAL: {p_app}. "
            f"DAG vinculado por HoTT engine. "
            f"Centuria Expansion Phase {'6' if p_num <= 75 else '7'}. "
            f"Sello: borjamoskv."
        )

        try:
            event_hash = await hott_engine.ingest_axiom(
                agent_idx=agent_id,
                axiom_claim=axiom_claim,
                constructive_proof=constructive_proof,
            )
            logger.info(
                f"[{i+1:02d}/{total}] {p_id} → Hash: {event_hash[:16]}..."
            )
            ultramap.update_agent_position(
                agent_id,
                50.0 + (i + 1) * 1.0,
                0.0,
                0.0,
                "MOSKV1_APEX_CENTURIA_LEAF",
                0.1,
            )
            success_count += 1
        except Exception as e:
            logger.error(f"[{i+1:02d}/{total}] {p_id} FAILED: {e}")
            fail_count += 1

    logger.info(
        f"Inyección Centuria completada. "
        f"Éxito: {success_count} | Fallos: {fail_count}"
    )
    await asyncio.sleep(1.0)


if __name__ == "__main__":
    asyncio.run(inject_centuria())
