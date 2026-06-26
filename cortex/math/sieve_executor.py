# C5-REAL
import sys
import uuid
import sqlite3
import hashlib
from datetime import datetime, timezone
import logging

from cortex.math.riemann_sieve import get_riemann_zero
from cortex.nodes.riemann_hypothesis_nodes import RiemannZeroNode

# Logger C5-REAL
logging.basicConfig(level=logging.INFO, format='%(asctime)s | C5-REAL | %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = '/tmp/cortex_test_riemann.db'

def generate_taint(n_index: int, t_fixed: str) -> str:
    agent_id = "OUROBOROS-SIEVE"
    session_id = "C5-RESURRECTION"
    timestamp = datetime.now(timezone.utc).isoformat()
    raw = f"{agent_id}:{session_id}:{n_index}:{t_fixed}".encode('utf-8')
    sha3 = hashlib.sha3_256(raw).hexdigest()
    return f"taint:{agent_id}:{session_id}:{timestamp}:{sha3}"

def execute_sieve_batch(start_n: int, count: int):
    logger.info(f"Iniciando Tamizado Ouroboros V2. Rango: {start_n} a {start_n + count - 1}")
    
    conn = sqlite3.connect(DB_PATH, timeout=5000)
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
            
            # Inserción WAL atómica respetando schema previo + taint_signature
            cursor.execute('''
                INSERT OR REPLACE INTO riemann_zeros 
                (id, n_index, imaginary_part_scaled, scale_factor, real_part_scaled, hash, injected_at, taint_signature)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (node.id, node.n_index, node.imaginary_part_scaled, node.scale_factor, 
                  node.real_part_scaled, node.hash, node.injected_at, node.taint_signature))
            
            logger.info(f"Inyectado [N={n}] -> MILLENNIUM-RIEMANN-{n:06d} | Hash: {node.hash} | Taint: {node.taint_signature[:20]}...")
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Apoptosis de Lote: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Uso: python -m cortex.math.sieve_executor <start_n> <count>")
        sys.exit(1)
    start_n = int(sys.argv[1])
    count = int(sys.argv[2])
    execute_sieve_batch(start_n, count)
