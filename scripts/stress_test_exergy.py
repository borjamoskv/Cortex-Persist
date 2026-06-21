import time
import json
import random
import logging
from concurrent.futures import ThreadPoolExecutor

from cortex_rs import validate_exergy_mutation

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] %(message)s")
logger = logging.getLogger("EXERGY_STRESS")

def run_stress_test(num_mutations=50000, max_workers=64):
    logger.info(f"--- INICIANDO ESTRÉS EXERGÉTICO: {num_mutations} mutaciones, {max_workers} hilos ---")
    
    valid_nodes = [f"node_{i}" for i in range(100)]
    
    # Pre-generate payloads to isolate PyO3 execution time
    payloads = []
    logger.info("Generando payloads...")
    for i in range(num_mutations):
        # 80% chance of valid node, 20% chance of invalid (ghost) node
        is_valid_node = random.random() < 0.8
        node_id = random.choice(valid_nodes) if is_valid_node else f"ghost_{i}"
        
        # 90% chance of sufficient signatures, 10% insufficient
        sufficient_sigs = random.random() < 0.9
        sigs = ["n1", "n2", "n3", "n4", "n5", "n6"] if sufficient_sigs else ["n1", "n2"]
        
        mutation = {
            "node_id": node_id,
            "delta": random.uniform(-50.0, 50.0),
            "reason": "stress_test",
            "epoch_ms": int(time.time() * 1000),
            "signatures": sigs,
            "zk_proof": None,
            "rul_claim_id": "claim_valid_123"
        }
        payloads.append(json.dumps(mutation))

    logger.info("Lanzando ataque PyO3...")
    
    counters = {
        "success": 0,
        "err_node_not_found": 0,
        "err_insufficient_sigs": 0,
        "err_other": 0
    }
    
    def process_mutation(payload):
        try:
            # We pass the valid nodes to the Rust engine
            validate_exergy_mutation(payload, valid_nodes)
            return "success"
        except Exception as e:
            msg = str(e)
            if "NodeNotFound" in msg:
                return "err_node_not_found"
            elif "InsufficientConsensus" in msg:
                return "err_insufficient_sigs"
            else:
                return "err_other"

    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(process_mutation, payloads)
        for r in results:
            counters[r] += 1
            
    total_time = time.time() - start_time
    rps = num_mutations / total_time
    
    logger.info("--- RESULTADOS DE AUDITORÍA ---")
    logger.info(f"Tiempo Total: {total_time:.4f}s")
    logger.info(f"Throughput (RPS): {rps:.2f} req/s")
    logger.info(f"Éxitos (Mutaciones Aprobadas): {counters['success']}")
    logger.info(f"Rechazos (NodeNotFound): {counters['err_node_not_found']}")
    logger.info(f"Rechazos (Firma Insuficiente): {counters['err_insufficient_sigs']}")
    logger.info(f"Rechazos (Otros): {counters['err_other']}")
    
    assert counters["err_node_not_found"] > 0, "No se detectaron fallas topológicas. Error en el binding."
    
if __name__ == "__main__":
    run_stress_test()
