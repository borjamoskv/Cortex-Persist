#!/usr/bin/env python3
"""
CORTEX-SENTINEL v2.
C5-REAL.
AST-Validated Pre-commit & Diff-Context Commit Forge.
"""

import sys
import os
import subprocess
import re
import ast
import math
from pathlib import Path

# --- CONSTANTS & CONFIG ---
CORTEX_NOIR_BLUE = "\033[38;2;43;59;229m"
CORTEX_NOIR_RED = "\033[38;2;255;50;50m"
CORTEX_RESET = "\033[0m"


def print_cortex(msg, error=False):
    color = CORTEX_NOIR_RED if error else CORTEX_NOIR_BLUE
    prefix = "[CORTEX-SENTINEL: C5-DEATH]" if error else "[CORTEX-SENTINEL: C5-REAL]"
    sys.stdout.write(f"{color}{prefix} {msg}{CORTEX_RESET}\n")


def get_staged_diff():
    result = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True)
    return result.stdout


def get_staged_files():
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"], capture_output=True, text=True
    )
    return [f for f in result.stdout.splitlines() if f.strip()]


def calculate_shannon_entropy(data: str) -> float:
    """C5-REAL: Calculate Shannon entropy."""
    if not data:
        return 0
    entropy = 0
    for x in set(data):
        p_x = float(data.count(x)) / len(data)
        entropy -= p_x * math.log(p_x, 2)
    return entropy


class ASTTrashDetector(ast.NodeVisitor):
    def __init__(self):
        self.has_trash = False
        self.trash_nodes = []

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            self.has_trash = True
            self.trash_nodes.append(f"print():{node.lineno}")
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name in ("pdb", "ipdb"):
                self.has_trash = True
                self.trash_nodes.append(f"import {alias.name}:{node.lineno}")
        self.generic_visit(node)


def run_pre_commit():
    files = get_staged_files()
    if not files:
        return 0

    diff = get_staged_diff()

    # 1. AST Analysis
    for file_path in files:
        if not file_path.endswith(".py") or not os.path.exists(file_path):
            continue
        try:
            with open(file_path, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=file_path)

            detector = ASTTrashDetector()
            detector.visit(tree)

            if detector.has_trash:
                print_cortex(
                    f"AST-VETO: {file_path} -> {', '.join(detector.trash_nodes)}",
                    error=True,
                )
                return 1
        except SyntaxError:
            print_cortex(f"AST-VETO: SyntaxError {file_path}", error=True)
            return 1

    # 2. Entropy Analysis
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            tokens = re.findall(r"[a-zA-Z0-9_\-]{20,}", line)
            for token in tokens:
                entropy = calculate_shannon_entropy(token)
                if entropy > 4.5:
                    print_cortex(
                        f"ENTROPY-VETO: E={entropy:.2f} {token[:6]}...",
                        error=True,
                    )
                    return 1

    print_cortex("Pre-commit: PASS.")
    return 0


def _extract_diff_context(diff: str) -> list:
    """C5-REAL: Extract diff chunk headers."""
    context = []
    for line in diff.splitlines():
        if line.startswith("@@"):
            match = re.search(r"@@.*@@\s+(.*)", line)
            if match and match.group(1):
                clean_name = (
                    match.group(1).split("(")[0].replace("def ", "").replace("class ", "").strip()
                )
                if clean_name and clean_name not in context:
                    context.append(clean_name)
    return context


def run_prepare_commit_msg(commit_msg_file):
    try:
        with open(commit_msg_file) as f:
            current_msg = f.read().strip()
    except FileNotFoundError:
        current_msg = ""

    if current_msg and not current_msg.startswith("auto") and not current_msg.startswith("#"):
        return 0

    files = get_staged_files()
    if not files:
        return 0

    diff = get_staged_diff()
    modified_scopes = _extract_diff_context(diff)

    type_tag = "chore"
    if any(f.endswith(".py") for f in files):
        if any("tests" in f for f in files):
            type_tag = "test"
        else:
            type_tag = "feat" if len(modified_scopes) > 0 else "fix"
    elif any(f.endswith(".md") for f in files):
        type_tag = "docs"

    scope = modified_scopes[0] if modified_scopes else Path(files[0]).parent.name
    if scope in (".", ""):
        scope = "core"

    auto_msg = f"{type_tag}({scope}): update context\n\n[CORTEX-SENTINEL: C5-REAL]\n"

    if modified_scopes:
        auto_msg += f"- Scopes: {', '.join(modified_scopes[:5])}\n"

    with open(commit_msg_file, "w") as f:
        f.write(auto_msg + current_msg)

    print_cortex(f"Forge: {type_tag}({scope})")
    return 0


def main():
    hook_name = Path(sys.argv[0]).name

    if hook_name == "pre-commit":
        sys.exit(run_pre_commit())
    elif hook_name == "prepare-commit-msg":
        if len(sys.argv) > 1:
            sys.exit(run_prepare_commit_msg(sys.argv[1]))
        else:
            sys.exit(0)
    else:
        print_cortex("Installing C5-REAL hooks...")
        repo_root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
        ).stdout.strip()
        if not repo_root:
            print_cortex("ERR: Not a git repo.", error=True)
            sys.exit(1)

        hooks_dir = Path(repo_root) / ".git" / "hooks"
        target_script = Path(__file__).resolve()

        for hook in ["pre-commit", "prepare-commit-msg"]:
            hook_path = hooks_dir / hook
            if hook_path.exists():
                hook_path.unlink()
            os.symlink(target_script, hook_path)
            hook_path.chmod(0o755)
            print_cortex(f"Link: {hook} -> {target_script}")

        sys.exit(0)


if __name__ == "__main__":
    main()
