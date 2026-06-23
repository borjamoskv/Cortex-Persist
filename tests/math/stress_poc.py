import time
import uuid
import hashlib
from babylon60.math.babylon import causal_distance, hash_distance_rollup

def generate_mock_trajectory() -> str:
    """Simulates a causal state hash."""
    return hashlib.sha256(uuid.uuid4().bytes).hexdigest()

def run_stress_test(num_inferences: int = 100_000, batch_size: int = 1_000):
    print("[C5-REAL] Iniciando PoC de Estrés - BABYLON-60")
    print(f"-> Ingestando {num_inferences:,} inferencias cognitivas.")
    print(f"-> Merkle Rollups de a {batch_size:,} nodos.\n")
    
    start_time = time.perf_counter()
    
    distances: list[tuple[str, str, int]] = []
    
    # 1. Simulación de Inferencia (Distancia Causal)
    dist_start = time.perf_counter()
    for i in range(num_inferences):
        # Simulamos overlaps determinísticos pseudo-aleatorios (usando modulo para ser 100% determinista)
        a_overlap = (i * 13) % 60
        w_overlap = (i * 7) % 30
        l_overlap = (i * 3) % 10
        t_overlap = (i * 17) % 100
        
        # Computamos distancia causal entera pura
        dist = causal_distance(a_overlap, l_overlap, w_overlap, t_overlap)
        
        # Mock de hashes para la trayectoria
        q_hash = f"Q_{(i * 101) % 999999}"
        t_hash = f"T_{(i * 202) % 999999}"
        
        distances.append((q_hash, t_hash, dist))
        
    dist_end = time.perf_counter()
    dist_time_ms = (dist_end - dist_start) * 1000
    
    print(f"[✔] Distancia Causal ({num_inferences:,} nodos): {dist_time_ms:.2f} ms")
    print(f"    -> {(dist_time_ms / num_inferences):.4f} ms por nodo.")
    
    # 2. Simulación de Merkle Rollups
    root_hash = "GENESIS_ROOT_0000000000000000000000000000000000000000000000000000"
    
    rollup_start = time.perf_counter()
    
    num_batches = num_inferences // batch_size
    for b in range(num_batches):
        batch = distances[b * batch_size : (b + 1) * batch_size]
        root_hash = hash_distance_rollup(root_hash, batch)
        
    rollup_end = time.perf_counter()
    rollup_time_ms = (rollup_end - rollup_start) * 1000
    
    print(f"[✔] Merkle Rollup ({num_batches} batches de {batch_size}): {rollup_time_ms:.2f} ms")
    print(f"    -> {(rollup_time_ms / num_batches):.4f} ms por batch de {batch_size}.")
    
    total_time = time.perf_counter() - start_time
    print("\n[!] RESULTADO FINAL: Estado Invariante")
    print(f"-> Raíz Merkle (Causal Root): {root_hash}")
    print(f"-> Tiempo Total: {total_time:.4f} s")
    
    # Assertions RFC-BABYLON-60 (Sección 11.3: < 10ms por transición)
    avg_transition_ms = (dist_time_ms + rollup_time_ms) / num_inferences
    if avg_transition_ms < 10.0:
        print(f"-> [PASS] Invariante de latencia cumplida: {avg_transition_ms:.4f} ms < 10ms")
    else:
        print(f"-> [FAIL] Violación termodinámica. Latencia: {avg_transition_ms:.4f} ms")

if __name__ == "__main__":
    run_stress_test(num_inferences=500_000, batch_size=5_000)
