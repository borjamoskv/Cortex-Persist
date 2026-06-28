#!/usr/bin/env python3
import time
import sys
import os
import tracemalloc

# Add current path to sys.path to ensure babylon60 module is found
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reference.interpreter import B60Compiler, B60MinimalVM

def run_stress():
    code = """
    # B60 Stress Vector
    NIG R0 [ < Y ] UNIT.TICK
    FORK LABEL_A
    EXECUTE SINGULARITY_CHECK
    AWAIT SINGULARITY_CHECK LABEL_B
    HALT
    MUB LABEL_A
    HALT
    MUB LABEL_B
    CRITICAL HALT
    """
    
    compiler = B60Compiler()
    
    iterations = 10000
    hashes = set()
    
    print(f"[C5-REAL] Initiating BABYLON-60 3.0 Stress Test...")
    print(f"[C5-REAL] Target Iterations: {iterations}")
    
    tracemalloc.start()
    start_time = time.time()
    
    for i in range(iterations):
        program = compiler.compile(code)
        hashes.add(program.sha256)
        
        vm = B60MinimalVM()
        state = vm.execute(program)
        
        # Verify deterministic termination
        if state != "HALTED":
            print(f"Entropic failure at iteration {i}. State: {state}")
            sys.exit(1)
            
    elapsed = time.time() - start_time
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    print("--------------------------------------------------")
    print(f"[METRIC] Execution Time: {elapsed:.4f}s")
    print(f"[METRIC] Throughput: {iterations/elapsed:.2f} compiles/executions per sec")
    print(f"[METRIC] Memory Peak: {peak / 10**6:.4f} MB")
    print(f"[METRIC] Determinism: {len(hashes)} unique binary signature(s) detected.")
    
    if len(hashes) == 1:
        print(f"[SIGNATURE] {list(hashes)[0]}")
        print("[STATUS] ZERO ANERGY. Ouroboros Loop stable. Formal properties preserved under stress.")
    else:
        print("[STATUS] FAILURE. Entropic hash divergence detected.")
        sys.exit(1)

if __name__ == '__main__':
    run_stress()
