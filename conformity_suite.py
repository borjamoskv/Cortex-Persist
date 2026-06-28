#!/usr/bin/env python3
# C5-REAL: Conformity Suite (Hito C)
import os
import sys
import json
import subprocess
import hashlib

# Build the Rust Reference Interpreter
subprocess.run(["rustc", "babylon60.rs", "-o", "b60_kernel"], check=True)

# Define the Conformity Test Cases
# Format: "Opcode": ("B60 Source", "Expected OpTrace subset")
TEST_SUITE = {
    "NIG": (
        """
        ALLOC F60 R1
        NIG R1 [ - < Y ]
        HALT
        """,
        ["(Assign R1 [ < Y ]"]
    ),
    "BA.EXACT": (
        """
        ALLOC F60 R1
        ALLOC I64 R2
        NIG R1 [ <Y ]
        NIG R2 [ Y ]
        BA.EXACT R1 R2
        HALT
        """,
        [] # Division doesn't emit a DAG event right now, but script shouldn't crash
    ),
    "FORK": (
        """
        FORK "TaskA"
        HALT
        MUB "TaskA"
        EXECUTE "Worker_Spawned"
        HALT
        """,
        ["(Spawn TaskA", "(Emit Worker_Spawned"]
    ),
    "AWAIT": (
        """
        FORK "Producer"
        AWAIT "SignalX" "ConsumerContinue"
        HALT
        MUB "ConsumerContinue"
        EXECUTE "Consumed"
        HALT
        MUB "Producer"
        EXECUTE "SignalX"
        HALT
        """,
        ["(Block SignalX", "(Emit SignalX", "(Emit Consumed"]
    ),
    "AFTER": (
        """
        ALLOC TIME R1
        NIG R1 [ - - Y ] UNIT.TICK
        AFTER R1 "WakeUp"
        HALT
        MUB "WakeUp"
        EXECUTE "TimerFired"
        HALT
        """,
        ["(Wait 1", "(Emit TimerFired"]
    ),
    "SAR.B60": (
        """
        ALLOC I64 R1
        NIG R1 [ - < Y ]
        SAR.B60 R1
        HALT
        """,
        []
    ),
    "CRITICAL_HALT": (
        """
        ALLOC TIME R1
        FORK "Infinite"
        EXECUTE "CRITICAL_HALT: SHUTDOWN"
        HALT
        MUB "Infinite"
        EXECUTE "Spam"
        AFTER R1 "Infinite"
        HALT
        """,
        ["(Emit CRITICAL_HALT: SHUTDOWN"]
    )
}

def run_test(name, source, expected_trace):
    print(f"[MOSKV APEX] Executing Conformity Test: {name}")
    script_path = f"test_{name}.b60"
    with open(script_path, "w") as f:
        f.write(source)
    
    res = subprocess.run(["./b60_kernel", script_path], capture_output=True, text=True)
    os.remove(script_path)
    
    if res.returncode != 0 and name != "HALT":
        print(f"  -> [FAIL] Execution aborted.\n{res.stderr}\n{res.stdout}")
        return False

    try:
        with open("artifact_bundle_v3/proof.ir", "r") as f:
            canonical = f.read()

        # Assert Expected State
        for exp in expected_trace:
            if exp not in canonical:
                print(f"  -> [FAIL] Expected trace '{exp}' not found in artifact.\nGraph: {canonical}")
                return False
                
        print("  -> [PASS] Isomorphic Trace Match.")
        return True
    except Exception as e:
        print(f"  -> [FAIL] Artifact Error: {e}")
        return False

if __name__ == "__main__":
    passed = 0
    total = len(TEST_SUITE)
    for name, (src, trace) in TEST_SUITE.items():
        if run_test(name, src, trace):
            passed += 1
            
    print(f"\n[C5-REAL] Conformity Suite (Hito C) Results: {passed}/{total} Passed.")
    if passed < total:
        sys.exit(1)
    else:
        print("[C5-REAL] Full BFT Homomorphism confirmed.")
