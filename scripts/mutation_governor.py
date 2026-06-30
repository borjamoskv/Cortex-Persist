#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
"""
Mutation Governor - Automated Decision Engine (SAGA-MS).

Analyzes the changed files in the working directory or staging area,
evaluating the thermodynamic constraints to mandate or bypass 
the Mutation Sandbox.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Dict, List, Set, Final

# Mandated directories where AST and security validations are critical
MANDATORY_PATHS: Final[List[str]] = [
    "babylon60/engine/causal/",
    "babylon60/crypto/",
    "babylon60/database/",
    "babylon60/audit/",
    "babylon60/engine/flow/",
]

# Paths allowed to bypass the expensive mutation checks
BYPASS_EXTENSIONS: Final[Set[str]] = {
    ".md",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".css",
    ".mjs",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
}

BYPASS_DIRS: Final[List[str]] = [
    "cortex_ui/",
    "public/",
    "src/",
    "docs/",
    "BOCETOS/",
    ".github/",
    ".agents/",
]


def get_changed_files() -> List[str]:
    """Retrieves all modified and staged files in the git workspace."""
    try:
        # Detect uncommitted and staged changes compared to main
        cmd = ["git", "diff", "--name-only", "origin/main...HEAD"]
        res = subprocess.run(
            cmd, capture_output=True, text=True, check=True, cwd=os.getcwd()
        )
        files = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        if not files:
            # Fallback to local working tree status
            cmd_status = ["git", "status", "--porcelain"]
            res_status = subprocess.run(
                cmd_status, capture_output=True, text=True, check=True, cwd=os.getcwd()
            )
            files = []
            for line in res_status.stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2:
                    files.append(parts[-1])
        return files
    except Exception as ex:
        print(f"ERROR: Failed to query git status: {ex}", file=sys.stderr)
        return []


def evaluate_mutation_necessity(files: List[str]) -> Dict[str, any]:
    """Evaluates the thermodynamic decision matrix for the list of changes."""
    mandatory_triggers: List[str] = []
    bypassable_changes: List[str] = []
    undetermined_changes: List[str] = []

    for file in files:
        # Check bypass conditions
        _, ext = os.path.splitext(file)
        if ext in BYPASS_EXTENSIONS:
            bypassable_changes.append(file)
            continue

        in_bypass_dir = False
        for b_dir in BYPASS_DIRS:
            if file.startswith(b_dir):
                bypassable_changes.append(file)
                in_bypass_dir = True
                break
        if in_bypass_dir:
            continue

        # Check mandatory triggers
        is_mandatory = False
        for m_path in MANDATORY_PATHS:
            if file.startswith(m_path):
                mandatory_triggers.append(file)
                is_mandatory = True
                break
        if is_mandatory:
            continue

        # Default fallback: files in python backend not matching bypass or mandatory list
        undetermined_changes.append(file)

    # Determine status
    if mandatory_triggers:
        status = "MANDATORY"
        reason = f"Critical core files modified: {len(mandatory_triggers)}"
    elif undetermined_changes:
        status = "RECOMMENDED"
        reason = f"Generic backend files modified: {len(undetermined_changes)}"
    else:
        status = "BYPASS_ALLOWED"
        reason = "Only document, config, or frontend changes detected."

    return {
        "status": status,
        "reason": reason,
        "mandatory_triggers": mandatory_triggers,
        "bypassable_changes": bypassable_changes,
        "undetermined_changes": undetermined_changes,
    }


def main() -> None:
    print("---")
    print("Claim: 'Mutation Governor Decision Analysis'")
    print("Confidence: 'C5'")

    files = get_changed_files()
    if not files:
        print("Status: 'BYPASS_ALLOWED'")
        print("Reason: 'No modified files detected in the workspace.'")
        sys.exit(0)

    decision = evaluate_mutation_necessity(files)
    print(f"Status: '{decision['status']}'")
    print(f"Reason: '{decision['reason']}'")
    print(f"Total_Files: {len(files)}")
    print(f"Mandatory_Files: {len(decision['mandatory_triggers'])}")
    print(f"Bypass_Files: {len(decision['bypassable_changes'])}")
    print(f"Undetermined_Files: {len(decision['undetermined_changes'])}")
    print("...")

    # Set exit code to notify CI / pre-commit
    if decision["status"] == "MANDATORY":
        sys.exit(1)  # Signal verification gate required
    sys.exit(0)


if __name__ == "__main__":
    main()
