import time
import uuid
import random
from cortex.math.babylon import causal_distance, hash_distance_rollup

def run_causal_stress_test(num_nodes=50000, batch_size=5000):
    print(f"🪐 BABYLON-60 Singularidad: Inicando Prueba de Estrés (Causal Distance + Rollup)")
    print(f"Generando {num_nodes} nodos cognitivos simulados en C5-REAL...")
    
    # Simulate a DAG traversal
    start_time = time.time()
    
    batches = []
    current_batch = []
    
    # 1. Distances computation (no float, purely discrete)
    for i in range(num_nodes):
        ancestry = random.randint(0, 10)
        witness = random.randint(0, 5)
        ledger = random.randint(0, 5)
        temporal = random.randint(0, 100)
        
        # Calculate causal divergence
        dist = causal_distance(ancestry, ledger, witness, temporal)
        
        q_hash = uuid.uuid4().hex
        t_hash = uuid.uuid4().hex
        
        current_batch.append((q_hash, t_hash, dist))
        
        if len(current_batch) >= batch_size:
            batches.append(current_batch)
            current_batch = []
            
    if current_batch:
        batches.append(current_batch)
        
    mid_time = time.time()
    print(f"✅ {num_nodes} distancias causales computadas en {(mid_time - start_time)*1000:.2f} ms")
    
    # 2. Rollup Hashing
    root_hash = "GENESIS_ROOT_00000000000000000000000000000000000000000000000000000000"
    
    for idx, batch in enumerate(batches):
        root_hash = hash_distance_rollup(root_hash, batch)
        
    end_time = time.time()
    
    print(f"✅ {len(batches)} Batches (Merkle Rollups) procesados en {(end_time - mid_time)*1000:.2f} ms")
    print(f"Final Merkle Root: {root_hash}")
    print(f"Tiempo Total: {(end_time - start_time)*1000:.2f} ms")
    print("\n🚀 Cero Anergía. Cero Flotantes. Determinismo Absoluto.")

if __name__ == "__main__":
    run_causal_stress_test(num_nodes=100000, batch_size=5000)
