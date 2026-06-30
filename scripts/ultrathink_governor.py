#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
"""
Ultrathink Governor - Automated Cognitive Decision Engine (SAGA-UT).

Calculates the Shannon Entropy, topological blast radius, and cognitive exergy
of git changes to automate the enforcement of the Ultrathink (P0) Horizon.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from typing import Optional

# Insert workspace root in path to ensure imports resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from babylon60.engine.core.ultrathink_physics import UltrathinkPhysicsEngine


def build_dependency_graph(root_dir: str) -> dict[str, list[str]]:
    """Builds a dependency graph of all python modules in the package."""
    graph: dict[str, list[str]] = {}
    # Matches: import babylon60.xxx or from babylon60.xxx import ...
    import_pat = re.compile(r"^\s*(?:import\s+(babylon60\.[a-zA-Z0-9_\.]+)|from\s+(babylon60\.[a-zA-Z0-9_\.]+)\s+import)")

    for root, _, files in os.walk(root_dir):
        for file in files:
            if not file.endswith(".py"):
                continue
            path = os.path.join(root, file)
            # Translate path to module name
            rel_path = os.path.relpath(path, os.path.dirname(root_dir))
            mod_name = os.path.splitext(rel_path)[0].replace(os.sep, ".")

            imports: list[str] = []
            try:
                with open(path, encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        match = import_pat.match(line)
                        if match:
                            imp = match.group(1) or match.group(2)
                            if imp:
                                imports.append(imp)
            except Exception:
                pass
            graph[mod_name] = list(set(imports))
    return graph


def get_git_diff() -> tuple[str, list[str]]:
    """Retrieves the git diff text and list of modified files."""
    try:
        # Diff against main
        cmd_diff = ["git", "diff", "origin/main...HEAD"]
        res_diff = subprocess.run(cmd_diff, capture_output=True, text=True, check=True)
        diff_text = res_diff.stdout

        cmd_files = ["git", "diff", "--name-only", "origin/main...HEAD"]
        res_files = subprocess.run(cmd_files, capture_output=True, text=True, check=True)
        files = [line.strip() for line in res_files.stdout.splitlines() if line.strip()]

        if not files:
            # Fallback to local unstaged/staged files
            cmd_diff = ["git", "diff", "HEAD"]
            res_diff = subprocess.run(cmd_diff, capture_output=True, text=True, check=True)
            diff_text = res_diff.stdout

            cmd_files = ["git", "diff", "--name-only", "HEAD"]
            res_files = subprocess.run(cmd_files, capture_output=True, text=True, check=True)
            files = [line.strip() for line in res_files.stdout.splitlines() if line.strip()]

        return diff_text, files
    except Exception as ex:
        print(f"ERROR: Failed to run git diff: {ex}", file=sys.stderr)
        return "", []


def main() -> None:
    print("---")
    print("Claim: 'Ultrathink Governor Autopilot Analysis'")
    print("Confidence: 'C5'")

    diff_text, files = get_git_diff()
    if not files:
        print("Status: 'BYPASS_ALLOWED'")
        print("Reason: 'No changes detected. Cognitive equilibrium preserved.'")
        sys.exit(0)

    # 1. Estimate Shannon Entropy of the changes
    entropy = UltrathinkPhysicsEngine.estimate_shannon_entropy(diff_text)

    # 2. Build dependency graph and compute blast radius
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    package_dir = os.path.join(workspace_root, "babylon60")
    graph = build_dependency_graph(package_dir)

    max_radius = 1
    epicenter_node: Optional[str] = None

    for file in files:
        if file.startswith("babylon60/") and file.endswith(".py"):
            mod_name = os.path.splitext(file)[0].replace("/", ".")
            if mod_name in graph:
                radius = UltrathinkPhysicsEngine.measure_blast_radius(graph, mod_name)
                if radius > max_radius:
                    max_radius = radius
                    epicenter_node = mod_name

    # Fallback to first python file if none found in graph
    if not epicenter_node:
        py_files = [f for f in files if f.endswith(".py")]
        if py_files:
            epicenter_node = os.path.splitext(py_files[0])[0].replace("/", ".")
        else:
            epicenter_node = files[0]

    # 3. Evaluate Authorization using Landauer Formula
    # S_stoc = entropy
    # S_det = S_stoc * 12.0 (simulating compressed output order)
    # T = 2.0s (execution latency)
    stochastic_entropy = entropy
    deterministic_output = entropy * 12.0
    execution_time = 2.0

    authorized, msg, formation = UltrathinkPhysicsEngine.authorize_ultrathink(
        stochastic_entropy=stochastic_entropy,
        deterministic_output=deterministic_output,
        execution_time=execution_time,
        epicenter_radius=max_radius,
        epicenter_node=epicenter_node,
    )

    print(f"Status: '{'MANDATED' if authorized else 'BYPASS_ALLOWED'}'")
    print(f"Reason: '{msg}'")
    print(f"Shannon_Entropy: {entropy:.4f}")
    print(f"Max_Blast_Radius: {max_radius}")
    print(f"Epicenter_Node: '{epicenter_node}'")
    if formation:
        print(f"Swarm_Formation: '{formation.value}'")
    print("...")

    # Exit code: 0 if bypass is allowed, 1 if Ultrathink P0 mode is required/mandated
    if authorized:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
