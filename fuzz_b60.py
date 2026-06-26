import sys
import os
import random
import subprocess
import json

def generate_program(seed, num_instructions):
    random.seed(seed)
    program = []
    
    # Pre-alloc registers to avoid unallocated panic
    program.append("ALLOC F60 R1")
    program.append("ALLOC I64 R2")
    program.append("ALLOC TIME R3")
    
    opcodes = ["NIG", "DAH", "LAL", "FORK", "AWAIT", "AFTER", "EXECUTE"]
    tasks = ["TaskA", "TaskB", "TaskC"]
    signals = ["SigX", "SigY", "SigZ"]
    
    for _ in range(num_instructions):
        op = random.choice(opcodes)
        reg = f"R{random.randint(1, 3)}"
        if op == "NIG":
            val = random.randint(1, 100)
            program.append(f"NIG {reg} [ {'Y' * min(val, 9)} ]")
        elif op == "DAH":
            val = random.randint(1, 10)
            program.append(f"DAH {reg} [ {'Y' * val} ]")
        elif op == "LAL":
            val = random.randint(1, 5)
            program.append(f"LAL {reg} [ {'Y' * val} ]")
        elif op == "FORK":
            target = random.choice(tasks)
            program.append(f"FORK \"{target}\"")
        elif op == "AWAIT":
            sig = random.choice(signals)
            target = random.choice(tasks)
            program.append(f"AWAIT \"{sig}\" \"{target}\"")
        elif op == "AFTER":
            # Using tick constant for deterministic timing fuzzing
            target = random.choice(tasks)
            program.append(f"AFTER {reg} \"{target}\"")
        elif op == "EXECUTE":
            sig = random.choice(signals)
            program.append(f"EXECUTE \"{sig}\"")
            
    program.append("HALT")
    
    # Add dummy labels for branch resolution
    for t in tasks:
        program.append(f"MUB \"{t}\"")
        program.append(f"EXECUTE \"Fallback_{t}\"")
        program.append("HALT")
        
    return "\n".join(program)

def run_fuzzer(iterations):
    print(f"[MOSKV APEX] Iniciando Property-Based Fuzzer ({iterations} iteraciones)...")
    subprocess.run(["rustc", "babylon60.rs", "-o", "b60_kernel"], check=True)
    
    for i in range(iterations):
        seed = i * 1337
        src = generate_program(seed, 20)
        script_path = f"fuzz_test_{i}.b60"
        
        with open(script_path, "w") as f:
            f.write(src)
            
        # Ejecutar 1:
        res1 = subprocess.run(["./b60_kernel", script_path], capture_output=True, text=True)
        if res1.returncode != 0:
            print(f"[FAIL] Panicked on seed {seed}!\n{res1.stderr}")
            sys.exit(1)
            
        with open("artifact_bundle_v3/graph.canonical", "r") as f:
            graph1 = f.read()
        with open("artifact_bundle_v3/proof.ir", "r") as f:
            ir1 = f.read()
            
        # Ejecutar 2: (Determinism check)
        res2 = subprocess.run(["./b60_kernel", script_path], capture_output=True, text=True)
        with open("artifact_bundle_v3/graph.canonical", "r") as f:
            graph2 = f.read()
        with open("artifact_bundle_v3/proof.ir", "r") as f:
            ir2 = f.read()
            
        os.remove(script_path)
            
        if graph1 != graph2 or ir1 != ir2:
            print(f"[FAIL] Determinism violation on seed {seed}!")
            sys.exit(1)
            
        if i % 10 == 0:
            print(f"  -> Progress: {i}/{iterations} (Reproducibilidad Determinista Confirmada)")
            
    print("[PASS] Fuzzing finalizado exitosamente. Cero divergencias detectadas.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=100)
    args = parser.parse_args()
    run_fuzzer(args.iterations)
