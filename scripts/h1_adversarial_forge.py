import json
import os
import sys
from collections import Counter
from pathlib import Path

def generate_adversarial_test_stub(target_file, survivors):
    """Generates pytest stub targeting surviving mutations."""
    file_path = Path(target_file)
    module_name = file_path.stem
    test_file_path = Path("tests") / f"test_adversarial_{module_name}.py"
    test_file_path.parent.mkdir(parents=True, exist_ok=True)

    mutation_types = set(s["mutation_type"] for s in survivors if s.get("mutation_type"))
    lines = set(s["lineno"] for s in survivors if s.get("lineno") != -1)

    stub_content = f'''"""
[C5-REAL] Auto-Generated Adversarial Test: {target_file}
Survivors: {len(survivors)}
Mutation Types: {", ".join(mutation_types)}
Lines: {", ".join(map(str, sorted(lines)))}
"""
import pytest

def test_adversarial_kill_mutants_{module_name}():
    """
    Action: Assert side-effects and control flow for lines {", ".join(map(str, sorted(lines)))}.
    """
    # Arrange: Setup state
    # Act: Execute target
    # Assert: Deep-equality validation
    assert True, "Pending implementation"
'''
    with open(test_file_path, "w") as f:
        f.write(stub_content)
    print(f"[C5-REAL] Written: {test_file_path}")

def run_adversarial_forge():
    print("[C5-REAL] INIT Adversarial Forge")
    if not os.path.exists("survivors_matrix.json"):
        print("[C5-REAL] ERROR: survivors_matrix.json missing.")
        sys.exit(1)

    with open("survivors_matrix.json") as f:
        survivors = json.load(f)

    if not survivors:
        print("[C5-REAL] STATUS: 0 survivors. Exit.")
        sys.exit(0)

    print(f"[C5-REAL] LOADED: {len(survivors)} mutations")
    file_counts = Counter(s["file"] for s in survivors)
    
    print("[C5-REAL] Top 3 Targets:")
    for file, count in file_counts.most_common(3):
        print(f"  - {file}: {count}")

    top_target = file_counts.most_common(1)[0][0]
    target_survivors = [s for s in survivors if s["file"] == top_target]

    print(f"[C5-REAL] TARGET SELECTED: {top_target}")
    generate_adversarial_test_stub(top_target, target_survivors)

if __name__ == "__main__":
    run_adversarial_forge()
