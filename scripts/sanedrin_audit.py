#!/usr/bin/env python3
"""
[C5-REAL] Sanedrín Daemon Script
Audits recent ledger entries using WBFTConsensus.
Created by Borja Moskv (borjamoskv).
"""
import asyncio
import hashlib
import json
import logging
import os
import sys

from cortex.audit.ledger import EnterpriseAuditLedger
from cortex.consensus.byzantine import WBFTConsensus
from cortex.extensions.thinking.fusion_models import ModelResponse
from cortex.extensions.llm.sovereign import SovereignLLM

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sanedrin")

def verify_ledger_cryptography(log_path: str, public_key) -> bool:
    """Verifies SHA-3-256 hash continuity and Ed25519 signatures in WORM log."""
    if not os.path.exists(log_path):
        logger.warning(f"Ledger file not found: {log_path}")
        return False

    try:
        import cortex_core_rs
    except ImportError:
        logger.error("cortex_core_rs extension not available for Merkle verification.")
        return False

    try:
        with open(log_path) as f:
            lines = f.readlines()
            
        if not lines:
            return True # Empty ledger is technically consistent (genesis state)

        prev_hash = "GENESIS"
        current_batch_hashes = []
        for line_num, line in enumerate(lines, 1):
            if not line.strip():
                continue
            event = json.loads(line)
            
            # Check BATCH_ROOT
            if event.get("type") == "BATCH_ROOT":
                if event.get("prev_hash") != prev_hash:
                    logger.error(f"Line {line_num}: prev_hash mismatch: expected {prev_hash}, got {event.get('prev_hash')}")
                    return False
                
                batch_root = event.get("batch_root")
                if not current_batch_hashes:
                    logger.error(f"Line {line_num}: BATCH_ROOT found with empty batch.")
                    return False
                
                computed_root = cortex_core_rs.batch_merkle_root(current_batch_hashes)
                if batch_root != computed_root:
                    logger.error(f"Line {line_num}: Merkle root mismatch: expected {computed_root}, got {batch_root}")
                    return False

                signature = event.get("signature")
                try:
                    public_key.verify(bytes.fromhex(signature), batch_root.encode("utf-8"))
                except Exception as e:
                    logger.error(f"Line {line_num}: BATCH_ROOT signature verification failed: {e}")
                    return False
                
                prev_hash = batch_root
                current_batch_hashes.clear()
                
            else:
                # Check standard event
                if event.get("parent_hash") != prev_hash:
                    logger.error(f"Line {line_num}: parent_hash mismatch: expected {prev_hash}, got {event.get('parent_hash')}")
                    return False
                
                payload = event.get("payload")
                payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
                
                # Check SHA3-256 hash chain
                m = hashlib.sha3_256()
                m.update(payload_str.encode("utf-8"))
                m.update(prev_hash.encode("utf-8"))
                expected_hash = m.hexdigest()
                
                if event.get("event_hash") != expected_hash:
                    logger.error(f"Line {line_num}: event_hash mismatch: expected {expected_hash}, got {event.get('event_hash')}")
                    return False
                
                # Verify Ed25519 signature
                signature = event.get("signature")
                try:
                    public_key.verify(bytes.fromhex(signature), payload_str.encode("utf-8"))
                except Exception as e:
                    logger.error(f"Line {line_num}: event signature verification failed: {e}")
                    return False
                
                current_batch_hashes.append(event.get("event_hash"))
                
        return True
    except Exception as e:
        logger.error(f"Ledger validation crashed: {e}")
        return False

async def audit_ledger():
    logger.info("🛡️ [SANEDRÍN] Invocando Quórum BFT para auditoría de estado...")
    
    # Check for custom ledger path from environment
    ledger_path = os.environ.get("CORTEX_LEDGER_PATH", "security_audit_log.jsonl")
    
    # Initialize ledger to fetch the correct config paths and public key
    ledger = EnterpriseAuditLedger(ledger_path)
    public_key = ledger.public_key
    log_path = ledger.log_path
    
    # Run the actual verification of the ledger WORM log file
    is_valid = verify_ledger_cryptography(log_path, public_key)
    
    # Check if we have API keys configured for real LLM evaluation
    has_keys = any(os.environ.get(k) for k in ["GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"])
    
    vote1 = None
    vote2 = None
    
    if has_keys:
        try:
            logger.info("Real LLM API keys detected. Querying SovereignLLM for votes...")
            async with SovereignLLM() as llm:
                prompt1 = (
                    f"You are Node 1 auditing the CORTEX-Persist WORM ledger. "
                    f"Cryptographic verification output: {is_valid}. "
                    f"If the verification output is True, output LEDGER_INTEGRITY_VERIFIED. "
                    f"If the verification output is False, output LEDGER_CORRUPTED. "
                    f"Output only the verdict and nothing else."
                )
                res = await llm.generate(prompt1)
                if res.is_template:
                    logger.warning("SovereignLLM fell back to template. Bypassing prompt parsing for Node 1.")
                    vote1 = None
                else:
                    content = res.content.strip().upper()
                    if "LEDGER_CORRUPTED" in content:
                        vote1 = "LEDGER_CORRUPTED"
                    elif "LEDGER_INTEGRITY_VERIFIED" in content:
                        vote1 = "LEDGER_INTEGRITY_VERIFIED"
                
                prompt2 = (
                    f"You are Node 2 auditing the CORTEX-Persist WORM ledger. "
                    f"Cryptographic verification output: {is_valid}. "
                    f"If the verification output is True, output LEDGER_INTEGRITY_VERIFIED. "
                    f"If the verification output is False, output LEDGER_CORRUPTED. "
                    f"Output only the verdict and nothing else."
                )
                res2 = await llm.generate(prompt2)
                if res2.is_template:
                    logger.warning("SovereignLLM fell back to template. Bypassing prompt parsing for Node 2.")
                    vote2 = None
                else:
                    content2 = res2.content.strip().upper()
                    if "LEDGER_CORRUPTED" in content2:
                        vote2 = "LEDGER_CORRUPTED"
                    elif "LEDGER_INTEGRITY_VERIFIED" in content2:
                        vote2 = "LEDGER_INTEGRITY_VERIFIED"
        except Exception as e:
            logger.warning(f"Real LLM call failed with error: {e}. Falling back to mocked inference.")
            
    # Graceful fallback to mocked inference
    if not vote1:
        logger.info("Using mocked inference for Node 1.")
        vote1 = "LEDGER_INTEGRITY_VERIFIED" if is_valid else "LEDGER_CORRUPTED"
    if not vote2:
        logger.info("Using mocked inference for Node 2.")
        vote2 = "LEDGER_INTEGRITY_VERIFIED" if is_valid else "LEDGER_CORRUPTED"
        
    # Node 3 is Byzantine (diverges or fails consensus to demonstrate fault tolerance)
    vote3 = "BYZANTINE_DIVERGENT_VOTE"

    # Format responses for WBFTConsensus
    responses = [
        ModelResponse(content=vote1, model="opus", provider="anthropic"),
        ModelResponse(content=vote2, model="gemini", provider="google"),
        ModelResponse(content=vote3, model="deepseek", provider="deepseek"),
    ]
    
    wbft = WBFTConsensus(byzantine_fraction=1/3, min_responses=3)
    verdict = wbft.evaluate(responses, domain="architecture")
    
    logger.info(f"⚖️ [SANEDRÍN] Veredicto: Confidence={verdict.confidence:.2f}, Trusted={verdict.trusted_count}, Outliers={len(verdict.outliers)}")
    
    if verdict.trusted_count >= 2 and verdict.best_response().content == "LEDGER_INTEGRITY_VERIFIED":
        logger.info("✅ [SANEDRÍN] Consenso Exitoso: Invariante del WORM Ledger confirmada sin entropía.")
    else:
        logger.error("❌ [SANEDRÍN] [P0] Falla Bizantina Catastrófica o Corrupción de Ledger detectada por el Sanedrín.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(audit_ledger())

