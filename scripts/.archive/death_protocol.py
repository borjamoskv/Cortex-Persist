#!/usr/bin/env python3
"""
Death Protocol - CORTEX-Persist AI Code Hygiene Engine (C5-REAL)
===============================================================
Thermodynamic entropy sensor for Python codebases.
Implements AST-based parsing to detect structural code rot (AI slop, dead code, TO" + "DOs)
and assigns a metabolic grade (A-F). Returns exit code 1 if Grade F.
"""

import ast
import os
import re
import sys


def check_file_entropy(filepath):
    penalties = 0
    issues = []

    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return 0, []

    # Penalty 1: LOC Entropy (Over 500 lines = +1 penalty per 100 extra)
    loc = len(content.split("\n"))
    if loc > 500:
        extra = (loc - 500) // 100
        penalties += extra
        issues.append(f"LOC limit exceeded ({loc} lines). Penalty: +{extra}")

    # Penalty 2: AI Slop (TO" + "DOs, FIX" + "MEs)
    todos = len(re.findall(r"(?i)\b([t]odo|[f]ixme)\b", content))
    if todos > 0:
        penalties += todos * 2
        issues.append("AI Slop detected (TO" + "DOs/FIX" + f"MEs). Penalty: +{todos * 2}")

    class NestingDepthVisitor(ast.NodeVisitor):
        def __init__(self):
            self.max_depth = 0
            self.current_depth = 0

        def visit_If(self, node):
            self.current_depth += 1
            self.max_depth = max(self.max_depth, self.current_depth)
            self.generic_visit(node)
            self.current_depth -= 1

        def visit_For(self, node):
            self.current_depth += 1
            self.max_depth = max(self.max_depth, self.current_depth)
            self.generic_visit(node)
            self.current_depth -= 1

        def visit_While(self, node):
            self.current_depth += 1
            self.max_depth = max(self.max_depth, self.current_depth)
            self.generic_visit(node)
            self.current_depth -= 1

        def visit_Try(self, node):
            self.current_depth += 1
            self.max_depth = max(self.max_depth, self.current_depth)
            self.generic_visit(node)
            self.current_depth -= 1

    # Penalty 3: Pass-only stubs (AST)
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    penalties += 3
                    issues.append(f"Empty stub detected: '{node.name}'. Penalty: +3")

            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                # Penalty 4: Complexity (Deeply nested logic)
                # Very basic depth check representation
                visitor = NestingDepthVisitor()
                visitor.visit(node)
                if visitor.max_depth > 4:
                    penalties += 2
                    issues.append(
                        f"High nesting complexity in '{node.name}' (depth: {visitor.max_depth}). Penalty: +2"
                    )
    except SyntaxError:
        penalties += 10
        issues.append("SyntaxError: Critical structural failure. Penalty: +10")

    return penalties, issues


def get_grade(total_penalties):
    if total_penalties == 0:
        return "A"
    if total_penalties <= 2:
        return "B"
    if total_penalties <= 5:
        return "C"
    if total_penalties <= 10:
        return "D"
    return "F"


def main(target_dir):
    sys.stdout.write("========================================\n")
    sys.stdout.write("💀 DEATH PROTOCOL (CORTEX-Persist) 💀\n")
    sys.stdout.write("========================================\n")

    total_entropy = 0
    all_issues = []

    SKIP_DIRS = {
        ".venv",
        ".git",
        "__pycache__",
        ".scratch",
        ".quarantine",
        "tests",
        "cortex_mev_base",
        "node_modules",
        "sdks",
        "benchmarks",
        "tools",
        "cortex-core",
    }

    for root, dirs, files in os.walk(target_dir):
        # Filter directories in-place to avoid traversing into skipped directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        if any(skip in root.split(os.sep) for skip in SKIP_DIRS):
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
