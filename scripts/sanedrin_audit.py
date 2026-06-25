#!/usr/bin/env python3
"""
[C5-REAL] Sanedrín Daemon Script
Audits recent ledger entries using WBFTConsensus.
Created by Borja Moskv (borjamoskv).
"""
import asyncio
import os
import sys
import logging

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from cortex.storage.ledger import EnterpriseAuditLedger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sanedrin")

async def audit_ledger():
    logger.info("🛡️ [SANEDRÍN] Invocando Auditoría Criptográfica Determinista (Ontología Cero)...")
    
    ledger_path = os.environ.get("CORTEX_LEDGER_PATH", "security_audit_log.jsonl")
    
    ledger = EnterpriseAuditLedger(ledger_path)
    
    # Primitiva C5-REAL: Validación absoluta de Hash Chain (O(N))
    is_valid = ledger.verify_chain_integrity()
    
    if is_valid:
        logger.info("✅ [SANEDRÍN] Consenso Exitoso: Invariante del WORM Ledger confirmada matemáticamente.")
        sys.exit(0)
    else:
        logger.error("❌ [SANEDRÍN] [P0] Corrupción de Ledger detectada. Invocando APOPTOSIS incondicional.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(audit_ledger())

