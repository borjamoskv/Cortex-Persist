#!/usr/bin/env python3
import subprocess
import sys
import os
import json
import shutil

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if result.returncode != 0:
        print(f"Error executing {cmd}:")
        print(result.stdout)
        print(result.stderr)
        sys.exit(1)
    return result.stdout

def get_bundle_hash(bundle_dir):
    manifest_path = os.path.join(bundle_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        return None
    with open(manifest_path, 'r') as f:
        data = json.load(f)
    return data.get("global_hash")

def get_canonical_graph(bundle_dir):
    graph_path = os.path.join(bundle_dir, "graph.canonical")
    if not os.path.exists(graph_path):
        return None
    with open(graph_path, 'r') as f:
        return f.read()

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 run_diff.py <script.b60>")
        sys.exit(1)
    
    script_path = sys.argv[1]
    bundle_dir = "artifact_bundle_v3"

    print(f"[Diff Validator] Testing {script_path}...")

    # 1. Run Python Reference Interpreter (Hito D1 Oracle)
    print("-> Running Reference VM (Python)...")
    if os.path.exists(bundle_dir):
        shutil.rmtree(bundle_dir)
    
    run_cmd(f"python3 reference/interpreter.py {script_path}")
    hash_ref = get_bundle_hash(bundle_dir)
    graph_ref = get_canonical_graph(bundle_dir)
    
    # 2. Run Optimized Rust VM
    print("-> Running Optimized VM (Rust)...")
    if os.path.exists(bundle_dir):
        shutil.rmtree(bundle_dir)
    
    # Compile rust VM just in case
    run_cmd("rustc babylon60.rs -o babylon60")
    run_cmd(f"./babylon60 {script_path}")
    hash_opt = get_bundle_hash(bundle_dir)
    graph_opt = get_canonical_graph(bundle_dir)

    # 3. Differential Verification
    if graph_ref is None or graph_opt is None:
        print("❌ [FAILED] Missing artifact bundles.")
        sys.exit(1)

    print(f"Reference Hash : {hash_ref}")
    print(f"Optimized Hash : {hash_opt}")

    if graph_ref == graph_opt:
        print("✅ [SUCCESS] Artifact A == Artifact B. Semantics preserved.")
    else:
        print("❌ [FAILED] Graph mismatch!")
        print("\n--- Reference Graph ---")
        print(graph_ref)
        print("\n--- Optimized Graph ---")
        print(graph_opt)
        sys.exit(1)

if __name__ == '__main__':
    main()
