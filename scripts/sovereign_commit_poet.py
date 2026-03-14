#!/usr/bin/env python3
"""
CORTEX Sovereign Commit Poet — prepare-commit-msg hook
========================================================
Intercepts the commit message and transforms it into compressed
literary prose using the LORCA-Ω engine.

INSTALLATION:
  ln -sf $(pwd)/scripts/sovereign_commit_poet.py .git/hooks/prepare-commit-msg
  chmod +x .git/hooks/prepare-commit-msg

USAGE (standalone dry-run):
  python scripts/sovereign_commit_poet.py --dry-run

DERIVATION: Axiom Ω₂ — reduce noise in the signal.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Add project root to path for cortex imports
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


CYAN = "\033[96m"
LIME = "\033[92m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"
YELLOW = "\033[93m"


def get_staged_diff_stat() -> str:
    """Get diff stat for staged changes."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--stat"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def get_staged_files() -> list[str]:
    """Get list of staged file paths."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRD"],
        capture_output=True,
        text=True,
    )
    return [f for f in result.stdout.strip().split("\n") if f]


def run_hook(commit_msg_file: str | None = None) -> int:
    """Main hook logic — generate and inject commit message."""
    from cortex.git.poet import CommitPoet

    diff_stat = get_staged_diff_stat()
    files = get_staged_files()

    if not files:
        return 0  # Nothing staged, nothing to do

    poet = CommitPoet()
    candidates = poet.compose_batch(diff_stat, files, count=3)

    if commit_msg_file:
        # prepare-commit-msg mode: write the best candidate
        msg_path = Path(commit_msg_file)
        existing = msg_path.read_text().strip() if msg_path.exists() else ""

        # Don't overwrite if user already wrote a message
        if existing and not existing.startswith("#"):
            return 0

        # Write the top candidate + alternatives as comments
        lines = [candidates[0], ""]
        if len(candidates) > 1:
            lines.append("# ── LORCA-Ω Alternatives ──────────────────────")
            for alt in candidates[1:]:
                lines.append(f"# {alt}")
            lines.append("# ──────────────────────────────────────────────")
        lines.append("")
        # Preserve any existing commented lines (git status, etc.)
        if existing:
            lines.append(existing)

        msg_path.write_text("\n".join(lines) + "\n")
    else:
        # Dry-run mode: just print
        print(f"\n{BOLD}{CYAN}╔══════════════════════════════════════════════════╗{RESET}")
        print(f"{BOLD}{CYAN}║  🖋️  LORCA-Ω — Sovereign Commit Poet            ║{RESET}")
        print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════╝{RESET}\n")

        print(f"{DIM}Staged files: {len(files)}{RESET}")
        print(f"{DIM}{diff_stat}{RESET}\n")

        for i, candidate in enumerate(candidates):
            marker = f"{LIME}★{RESET}" if i == 0 else f"{DIM}○{RESET}"
            print(f"  {marker} {BOLD if i == 0 else DIM}{candidate}{RESET}")

        print(f"\n{YELLOW}Top candidate would be used as your commit message.{RESET}\n")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="LORCA-Ω Sovereign Commit Poet",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print generated messages without modifying any files.",
    )
    parser.add_argument(
        "commit_msg_file",
        nargs="?",
        default=None,
        help="Path to the commit message file (set by git hook).",
    )
    parser.add_argument(
        "commit_source",
        nargs="?",
        default=None,
        help="Source of the commit (set by git hook).",
    )
    parser.add_argument(
        "commit_sha",
        nargs="?",
        default=None,
        help="SHA of the commit being amended (set by git hook).",
    )

    args = parser.parse_args()

    if args.dry_run:
        return run_hook(commit_msg_file=None)

    # Skip for merges, amends, squash, etc.
    if args.commit_source in ("merge", "squash", "commit"):
        return 0

    return run_hook(commit_msg_file=args.commit_msg_file)


if __name__ == "__main__":
    sys.exit(main())
