import asyncio
import logging
import time
import os
import sys

sys.path.insert(0, os.path.abspath('.'))

from cortex.storage.ledger import EnterpriseAuditLedger
from cortex.engine.autodidact_hott_engine import AutodidactHottEngine
from cortex.engine.ultramap import UltramapSubstrate

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("EndogenousSiege")

async def siege_worker(worker_id: int, iterations: int, hott_engine: AutodidactHottEngine):
    successes = 0
    for i in range(iterations):
        claim = f"SIEGE-{worker_id}-{i}: Operacion concurrente"
        proof = f"Aplicación estructural en C5-REAL: Verificacion de concurrencia BFT {worker_id}-{i}. DAG vinculado por HoTT engine."
        try:
            await hott_engine.ingest_axiom(
                agent_idx=worker_id,
                axiom_claim=claim,
                constructive_proof=proof
            )
            successes += 1
        except Exception as e:
            logger.error(f"Worker {worker_id} Failed at {i}: {e}")
    return successes

async def main():
    logger.info("Iniciando APEX-051 Endogenous Siege (Stress Test)...")
    ultramap = UltramapSubstrate(capacity=100000)
    ledger = EnterpriseAuditLedger(log_path="security_audit_log.jsonl")
    hott_engine = AutodidactHottEngine(ledger=ledger, ultramap=ultramap)
    
    WORKERS = 100
    ITERATIONS = 20
    logger.info(f"Desplegando Swarm (APEX-003) de {WORKERS} workers concurrentes. Op/Worker: {ITERATIONS}.")
    
    start_time = time.perf_counter()
    tasks = [
        asyncio.create_task(siege_worker(w_id, ITERATIONS, hott_engine))
        for w_id in range(WORKERS)
    ]
    
    results = await asyncio.gather(*tasks)
    end_time = time.perf_counter()
    
    total_success = sum(results)
    total_ops = WORKERS * ITERATIONS
    elapsed = end_time - start_time
    throughput = total_success / elapsed if elapsed > 0 else 0
    
    logger.info("=== RESULTADOS ENDOGENOUS SIEGE ===")
    logger.info(f"Total Operaciones Intentadas: {total_ops}")
    logger.info(f"Total Operaciones Exitosas: {total_success}")
    logger.info(f"Tiempo Transcurrido: {elapsed:.4f}s")
    logger.info(f"Throughput: {throughput:.2f} op/s")
    
    if total_success == total_ops:
        logger.info("Veredicto C5-REAL: ÉXITO ABSOLUTO. Anergía Cero. Sin Deadlocks Termodinámicos.")
    else:
        logger.warning(f"Veredicto C5-REAL: FRACTURA ESTRUCTURAL. {total_ops - total_success} fallos.")

if __name__ == "__main__":
    asyncio.run(main())
