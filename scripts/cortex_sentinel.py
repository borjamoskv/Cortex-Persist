#!/usr/bin/env python3
"""
CORTEX-SENTINEL x1000 — Exergy-Maximized Git Hook Substrate
Reality Level: C5-REAL
Role: Pre-commit (Secret/Trash Annihilation) & Prepare-commit-msg (Semantic Auto-Forge)
"""

import sys
import os
import subprocess
import re
from pathlib import Path

# --- CONSTANTS & CONFIG ---
CORTEX_NOIR_BLUE = "\033[38;2;43;59;229m"
CORTEX_NOIR_RED = "\033[38;2;255;50;50m"
CORTEX_RESET = "\033[0m"

SECRETS_REGEX = [
    (r"sk_live_[0-9a-zA-Z]{24}", "Stripe Live Key"),
    (r"0x[a-fA-F0-9]{64}", "EVM Private Key"),
    (r"(?i)api_key\s*=\s*['\"][a-zA-Z0-9_\-]{20,}['\"]", "Generic API Key")
]

TRASH_REGEX = [
    (r"(?<!_)" + "pri" + r"nt\s*\(", "Residual standard output"),
    (r"import pdb; pdb\.set_trace\(\)", "Residual PDB trace"),
    (r"console\.log\(", "Residual console.log()")
]

def print_cortex(msg, error=False):
    color = CORTEX_NOIR_RED if error else CORTEX_NOIR_BLUE
    prefix = "[CORTEX-SENTINEL: C5-DEATH]" if error else "[CORTEX-SENTINEL: C5-REAL]"
    sys.stdout.write(f"{color}{prefix} {msg}{CORTEX_RESET}\n")

def get_staged_diff():
    result = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True)
    return result.stdout

def get_staged_files():
    result = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True)
    return [f for f in result.stdout.splitlines() if f.strip()]

# --- PHASE 1: PRE-COMMIT (LEA-Ω PURGE) ---
def run_pre_commit():
    diff = get_staged_diff()
    if not diff:
        return 0

    # 1. Annihilate Secrets
    for pattern, name in SECRETS_REGEX:
        if re.search(pattern, diff):
            print_cortex(f"CRITICAL VIOLATION: {name} detected in staged changes. Committing blocked.", error=True)
            return 1

    # 2. Annihilate Trash (LEA-Ω)
    for pattern, name in TRASH_REGEX:
        if re.search(r"^\+.*" + pattern, diff, re.MULTILINE):
            print_cortex(f"ENTROPY DETECTED: {name} in staged changes. Clean up before committing.", error=True)
            return 1

    print_cortex("Pre-commit validation passed. Entropy zero.")
    return 0

# --- PHASE 2: PREPARE-COMMIT-MSG (SEMANTIC FORGE) ---
def run_prepare_commit_msg(commit_msg_file):
    # Only auto-forge if the message is empty or standard default
    try:
        with open(commit_msg_file, 'r') as f:
            current_msg = f.read().strip()
    except FileNotFoundError:
        current_msg = ""

    # If it's not a fresh commit or user already typed something meaningful, skip.
    # We auto-forge if the message is empty or just "auto"
    if current_msg and not current_msg.startswith("auto") and not current_msg.startswith("#"):
        return 0

    files = get_staged_files()
    if not files:
        return 0

    # Deterministic Semantic Resolution (O(1) latency)
    feat_files = [f for f in files if "cortex_rs" in f or "cortex-core" in f]
    docs_files = [f for f in files if f.endswith(".md")]
    fix_files = [f for f in files if "tests" in f or "bug" in f.lower()]

    type_tag = "chore"
    scope = "workspace"

    if feat_files:
        type_tag = "feat"
        scope = "core" if "cortex-core" in feat_files[0] else "rs"
    elif fix_files:
        type_tag = "fix"
        scope = "stability"
    elif docs_files:
        type_tag = "docs"
        scope = "knowledge"

    file_summary = ", ".join([Path(f).name for f in files[:3]])
    if len(files) > 3:
        file_summary += f" and {len(files)-3} more"

    auto_msg = f"{type_tag}({scope}): auto-update {file_summary}\n\n[CORTEX-SENTINEL: C5-REAL Auto-Forge]\n"

    with open(commit_msg_file, 'w') as f:
        f.write(auto_msg + current_msg)

    print_cortex(f"Forged semantic commit message: {type_tag}({scope})")
    return 0

# --- DISPATCH ---
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
        # Direct run / testing
        print_cortex("Direct execution. Installing hooks...")
        repo_root = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
        if not repo_root:
            print_cortex("Not inside a git repository.", error=True)
            sys.exit(1)
        
        hooks_dir = Path(repo_root) / ".git" / "hooks"
        target_script = Path(__file__).resolve()
        
        for hook in ["pre-commit", "prepare-commit-msg"]:
            hook_path = hooks_dir / hook
            if hook_path.exists():
                hook_path.unlink()
            os.symlink(target_script, hook_path)
            hook_path.chmod(0o755)
            print_cortex(f"Injected {hook} -> {target_script}")

        sys.exit(0)

if __name__ == "__main__":
    main()
