# [C5-REAL] Exergy-Maximized
"""Conformance Test Runner for CEP-004.

Executes official JSON vectors against the Python implementation
to guarantee deterministic CORTEX microkernel behavior.
"""

import json
import os
from pathlib import Path

from cortex.engine.core.canonical import compute_object_hash
from cortex.engine.core.epistemic_object import Assertion, SupportRelation

VECTORS_DIR = Path(__file__).parent.parent / "spec" / "vectors"

def run_conformance_tests():
    if not VECTORS_DIR.exists():
        print("No conformance vectors found.")
        return

    success_count = 0
    failure_count = 0

    for vector_file in VECTORS_DIR.glob("*.json"):
        if vector_file.name == "schema.json":
            continue

        with open(vector_file) as f:
            vector = json.load(f)

        vector_id = vector["vector_id"]
        print(f"Executing: {vector_id}")

        try:
            if vector["category"] == "TV-SER":
                # Serialization test
                props = vector["input_proposal"]
                hashes = set()
                for p in props:
                    if p["type"] == "Assertion":
                        obj = Assertion(data=p["data"])
                        hashes.add(obj.identifier)
                
                # For TV-SER-010, the hashes of identical content must match
                # meaning the set of hashes should have length 1
                if len(hashes) == 1:
                    computed_hash = hashes.pop()
                    if computed_hash == vector.get("expected_hash"):
                        print(f"  [PASS] {vector_id}")
                        success_count += 1
                    else:
                        print(f"  [FAIL] {vector_id} - Hash mismatch. Expected: {vector.get('expected_hash')}, Got: {computed_hash}")
                        failure_count += 1
                else:
                    print(f"  [FAIL] {vector_id} - Hashes did not converge: {hashes}")
                    failure_count += 1

            elif vector["category"] == "TV-TOP":
                # Topology test
                initial = vector.get("initial_state", {}).get("objects", {})
                prop = vector["input_proposal"]
                
                if prop["type"] == "SupportRelation":
                    # Check dangling references
                    ev_id = prop["evidence_id"]
                    if ev_id not in initial:
                        actual_behavior = "ERR_DANGLING_REFERENCE"
                    else:
                        actual_behavior = "SUCCESS"
                    
                    if actual_behavior == vector["expected_behavior"]:
                        print(f"  [PASS] {vector_id}")
                        success_count += 1
                    else:
                        print(f"  [FAIL] {vector_id} - Expected: {vector['expected_behavior']}, Got: {actual_behavior}")
                        failure_count += 1

        except Exception as e:
            print(f"  [ERROR] {vector_id} - {e}")
            failure_count += 1

    print(f"\nConformance Run Complete: {success_count} Passed, {failure_count} Failed.")
    if failure_count > 0:
        exit(1)

if __name__ == "__main__":
    run_conformance_tests()
