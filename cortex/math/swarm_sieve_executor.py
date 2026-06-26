# C5-REAL
import concurrent.futures
import hashlib
import logging
import sqlite3
import sys
import uuid
from datetime import datetime, timezone

from cortex.math.riemann_sieve import get_riemann_zero
from cortex.nodes.riemann_hypothesis_nodes import RiemannZeroNode

# Logger C5-REAL
logging.basicConfig(level=logging.INFO, format='%(asctime)s | C5-REAL | %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = '/tmp/cortex_test_riemann.db'

def generate_taint(n_index: int, t_fixed: str) -> str:
    agent_id = "OUROBOROS-SWARM"
    session_id = "C5-RESURRECTION"
    timestamp = datetime.now(timezone.utc).isoformat()
    raw = f"{agent_id}:{session_id}:{n_index}:{t_fixed}".encode()
    sha3 = hashlib.sha3_256(raw).hexdigest()
    return f"taint:{agent_id}:{session_id}:{timestamp}:{sha3}"

def execute_sieve_chunk(start_n: int, count: int, worker_id: int):
    logger.info(f"[Worker-{worker_id}] Iniciando chunk. Rango: {start_n} a {start_n + count - 1}")
    
    conn = sqlite3.connect(DB_PATH, timeout=10000)
    conn.execute("PRAGMA journal_mode=WAL")
    cursor = conn.cursor()
    
    try:
        for i in range(count):
            n = start_n + i
            
            t_fixed = get_riemann_zero(n)
            taint = generate_taint(n, t_fixed)
            
            # SAGA-3: Nodo Epistémico y Hash C5
            scale_factor_str = str(10**20)
            real_scaled = str(int(0.5 * 10**20))
            node_id = str(uuid.uuid4())
            injected_ts = datetime.now(timezone.utc).isoformat()
            
            node = RiemannZeroNode(
                id=node_id,
                n_index=n,
                imaginary_part_scaled=t_fixed,
                scale_factor=scale_factor_str,
                real_part_scaled=real_scaled,
                hash="",
                injected_at=injected_ts,
                taint_signature=taint
            )
            node.hash = node.compute_hash()
            
            # Inserción WAL atómica (concurrency safe with busy_timeout)
            cursor.execute('''
                INSERT OR REPLACE INTO riemann_zeros 
                (id, n_index, imaginary_part_scaled, scale_factor, real_part_scaled, hash, injected_at, taint_signature)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (node.id, node.n_index, node.imaginary_part_scaled, node.scale_factor, 
                  node.real_part_scaled, node.hash, node.injected_at, node.taint_signature))
            
            logger.info(f"[Worker-{worker_id}] Inyectado [N={n}] -> MILLENNIUM-RIEMANN-{n:06d} | Hash: {node.hash} | Taint: {node.taint_signature[:20]}...")
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"[Worker-{worker_id}] Apoptosis de Chunk: {e}")
        return False
    finally:
        conn.close()

def orchestrate_swarm(start_n: int, total_count: int, num_workers: int):
    logger.info(f"Levantando Ouroboros Swarm V3. Total: {total_count} ceros, Workers: {num_workers}")
    chunk_size = total_count // num_workers
    remainder = total_count % num_workers

    futures = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        current_n = start_n
        for w in range(num_workers):
            c_size = chunk_size + (1 if w < remainder else 0)
            if c_size > 0:
                futures.append(executor.submit(execute_sieve_chunk, current_n, c_size, w))
                current_n += c_size

        for future in concurrent.futures.as_completed(futures):
            if not future.result():
                logger.error("Error crítico en uno de los Swarm Workers.")
                sys.exit(1)
    
    logger.info("Swarm Batch completado en BFT.")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Uso: python -m cortex.math.swarm_sieve_executor <start_n> <total_count> [num_workers=10]")
        sys.exit(1)
    
    start_n = int(sys.argv[1])
    total_count = int(sys.argv[2])
    num_workers = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    
    orchestrate_swarm(start_n, total_count, num_workers)
