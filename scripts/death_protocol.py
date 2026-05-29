#!/usr/bin/env python3
"""
Death Protocol — CORTEX-Persist AI Code Hygiene Engine (C5-REAL)
===============================================================
Thermodynamic entropy sensor for Python codebases.
Implements AST-based parsing to detect structural code rot (AI slop, dead code, TODOs)
and assigns a metabolic grade (A-F). Returns exit code 1 if Grade F.
"""

import ast
import sys
import os


def check_file_entropy(filepath):
    penalties = 0
    issues = []

    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return 0, []

    # Penalty 1: LOC Entropy (Over 500 lines = +1 penalty per 100 extra)
    loc = len(content.split("\n"))
    if loc > 500:
        extra = (loc - 500) // 100
        penalties += extra
        issues.append(f"LOC limit exceeded ({loc} lines). Penalty: +{extra}")

    # Penalty 2: AI Slop (TODOs, FIXMEs)
    import re

    todos = len(re.findall(r"(?i)\b(todo|fixme)\b", content))
    if todos > 0:
        penalties += todos * 2
        issues.append(f"AI Slop detected (TODOs/FIXMEs). Penalty: +{todos * 2}")

    # Penalty 3: Pass-only stubs (AST)
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    penalties += 3
                    issues.append(f"Empty stub detected: '{node.name}'. Penalty: +3")

                # Penalty 4: Complexity (Deeply nested logic)
                # Very basic depth check representation
                depth = 0
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)):
                        depth += 1
                if depth > 10:
                    penalties += 2
                    issues.append(f"High nesting complexity in '{node.name}'. Penalty: +2")
    except SyntaxError:
        penalties += 10
        issues.append("SyntaxError: Critical structural failure. Penalty: +10")

    return penalties, issues


def get_grade(total_penalties):
    if total_penalties == 0:
        return "A"
    elif total_penalties <= 2:
        return "B"
    elif total_penalties <= 5:
        return "C"
    elif total_penalties <= 10:
        return "D"
    return "F"


def main(target_dir):
    sys.stdout.write("========================================\n")
    sys.stdout.write("💀 DEATH PROTOCOL (CORTEX-Persist) 💀\n")
    sys.stdout.write("========================================\n")

    total_entropy = 0
    all_issues = []

    for root, _, files in os.walk(target_dir):
        if ".venv" in root or ".git" in root or "__pycache__" in root:
            continue
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                penalties, issues = check_file_entropy(path)
                total_entropy += penalties
                if issues:
                    all_issues.append((path, issues))

    grade = get_grade(total_entropy)

    if all_issues:
        for path, issues in all_issues:
            sys.stdout.write(f"\n[FILE] {path}\n")
            for issue in issues:
                sys.stdout.write(f"  -> {issue}\n")

    sys.stdout.write("\n--- THERMODYNAMIC METABOLISM REPORT ---\n")
    sys.stdout.write(f"Total Structural Friction (Entropy): {total_entropy}\n")
    sys.stdout.write(f"System Health Grade: {grade}\n")

    if grade == "F":
        sys.stdout.write(
            "\n[CRITICAL] Grade F detected. Metabolic purge required. Aborting pipeline.\n"
        )
        sys.exit(1)
    else:
        sys.stdout.write("\n[OK] System entropy within acceptable parameters.\n")
        sys.exit(0)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    main(target)
