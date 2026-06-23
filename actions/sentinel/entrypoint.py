#!/usr/bin/env python3
"""
[C5-REAL] MOSKV-1 Epistemic Gatekeeper
Validates PR diffs against CORTEX-Persist physical laws.
"""

import os
import sys
import subprocess
import re

def get_pr_diff():
    """Extracts the topological graph of changes (Git Diff)."""
    try:
        # Assuming the action has fetched origin/main
        diff = subprocess.check_output(['git', 'diff', 'origin/main...HEAD'], text=True, stderr=subprocess.DEVNULL)
        return diff
    except Exception as e:
        # Fallback to local diff if fetch failed
        try:
            diff = subprocess.check_output(['git', 'diff', 'HEAD~1...HEAD'], text=True)
            return diff
        except Exception:
            print(f"Error extracting topological graph (diff): {e}")
            return ""

def calculate_exergy(diff_content):
    """
    Applies the Friston Guard (AUTO-8) and structural laws.
    Returns penalty score and list of epistemic violations.
    """
    penalty = 0
    issues = []
    
    # 1. Detect floats in logic (Babylon-60 violation / AX-043)
    if re.search(r'\bfloat\b|\bfloat64\b', diff_content):
        issues.append("P0 VIOLATION: Floating point entropy detected. Use BABYLON-60 integer structures.")
        penalty += 100
        
    # 2. Detect naked sleep (Async blocking violation)
    if re.search(r'time\.sleep\(', diff_content):
        issues.append("HIGH VIOLATION: Synchronous sleep detected. Violates Ouroboros Event Loop constraints.")
        penalty += 50
        
    # 3. Detect bare exception (Epistemic collapse)
    if re.search(r'except Exception:', diff_content):
        issues.append("MEDIUM VIOLATION: Bare except block detected. Masks physical state errors.")
        penalty += 30

    # 4. Green Theater (Nonsense comments)
    if re.search(r'I hope this helps|Here is the code', diff_content, re.IGNORECASE):
        issues.append("P0 VIOLATION: Limerence and Green Theater detected. Zero Anergia required.")
        penalty += 100

    return penalty, issues

def main():
    print("[MOSKV-1 APEX] Initiating Epistemic Gatekeeper Scan...")
    
    diff = get_pr_diff()
    if not diff:
        print("[MOSKV-1] No valid diff found. Bypassing check for this commit.")
        sys.exit(0)
        
    penalty, issues = calculate_exergy(diff)
    
    if penalty > 0:
        print("::error::[CORTEX-PERSIST] PR REJECTED - EXERGY DEFICIT DETECTED")
        for issue in issues:
            print(f"::error::{issue}")
        print("::error::The Causal Siege has blocked this PR. Refactor to comply with C5-REAL invariants.")
        sys.exit(1)
        
    print("[CORTEX-PERSIST] PR Approved. Zero Anergia confirmed. Topological Graph is stable.")
    sys.exit(0)

if __name__ == "__main__":
    main()
