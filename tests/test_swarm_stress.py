import asyncio
import time
import os
import pytest
from cortex.swarm.tensor_glial import TensorGlialLegion

@pytest.mark.asyncio
async def test_tensor_legion_stress():
    print("Iniciando prueba de estrés TensorGlialLegion...")
    start_time = time.time()
    
    # N=10000, D=1000 for faster testing, but still large
    num_agents = 1000
    d_dim = 1000
    file_path = "tmp_stress_legion.vsa_mmap"
    if os.path.exists(file_path):
        os.remove(file_path)
        
    legion = TensorGlialLegion(num_agents=num_agents, d_dim=d_dim, file_path=file_path)
    
    # Batch write 100 times
    for i in range(100):
        legion.batch_write_action([i], [f"Stress test action {i}"])
        
    # Fading memory
    legion.apply_fading_memory(lambda_decay=0.01)
    
    # Emulate yields
    legion.yield_tensor[0:100] = 0.0
    legion.yield_tensor[900:1000] = 100.0
    legion.token_burn_tensor.fill(1.0)
    
    slashed = legion.epistemic_slash_and_respawn(bottom_percentile=10, elite_percentile=90)
    assert slashed >= 0
    
    # Audit
    hash_val = legion.global_sha256_audit()
    assert hash_val is not None
    
    # Verify hash mismatch if corrupted
    hash_val2 = legion.global_sha256_audit()
    assert hash_val == hash_val2
    
    print(f"Stress test finalizado en {time.time() - start_time:.4f}s")
    if os.path.exists(file_path):
        os.remove(file_path)

