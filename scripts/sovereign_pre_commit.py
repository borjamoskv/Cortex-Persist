#!/usr/bin/env python3
"""
CORTEX Sovereign Pre-Commit Hook
=================================
Last line of defense against credential/seed leaks.
Catches what .gitignore cannot — including `git add -f`.

DERIVATION: Ω₃ Byzantine Default — verify, then trust.
"""

import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _changed_files import changed_files, run_git

# ── Forbidden patterns (case-insensitive) ─────────────────────
FORBIDDEN_PATTERNS: list[re.Pattern] = [
    re.compile(r"wallet_seed", re.IGNORECASE),
    re.compile(r"\.seed\.json$", re.IGNORECASE),
    re.compile(r"private[_-]?key\.json$", re.IGNORECASE),
    re.compile(r"\.pem$", re.IGNORECASE),
    re.compile(r"\.p12$", re.IGNORECASE),
    re.compile(r"\.pfx$", re.IGNORECASE),
    re.compile(r"credentials\.json$", re.IGNORECASE),
    re.compile(r"service[_-]account.*\.json$", re.IGNORECASE),
]

# ── Content patterns (detect secrets inside files) ────────────
CONTENT_PATTERNS: list[re.Pattern] = [
    re.compile(r"wallet_seed", re.IGNORECASE),
    re.compile(r"private_key.*0x[0-9a-fA-F]{40,}", re.IGNORECASE),
    re.compile(r"mnemonic.*(?:\b\w+\b\s+){11,}\b\w+\b"),
]

RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def get_staged_files() -> list[str]:
    """Get list of files staged for commit."""
    paths, source = changed_files(include_untracked=False, prefer_staged=True)
    if source != "staged":
        return []
    return [str(path) for path in paths]


def get_candidate_files() -> tuple[list[str], str, set[str]]:
    """Prefer staged files, but fall back to the local diff when the index is empty."""
    paths, source = changed_files(include_untracked=True, prefer_staged=True)
    files = [str(path) for path in paths]
    tracked_paths = changed_files(include_untracked=False, prefer_staged=True)[0]
    tracked = {str(path) for path in tracked_paths}
    untracked = {path for path in files if path not in tracked}
    return files, source, untracked


def check_filenames(files: list[str]) -> list[str]:
    """Check staged filenames against forbidden patterns."""
    violations: list[str] = []
    for filepath in files:
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(filepath):
                violations.append(f"  🚫 FILENAME: {filepath} (matched: {pattern.pattern})")
                break
    return violations


def _extract_added_lines(diff_content: str) -> str:
    added_lines: list[str] = []
    for line in diff_content.splitlines():
        if line.startswith(("diff --git ", "index ", "@@ ", "--- ", "+++ ")):
            continue
        if line.startswith("+"):
            added_lines.append(line[1:])
    return "\n".join(added_lines)


def _read_candidate_content(filepath: str, *, source: str, untracked_files: set[str]) -> str:
    diff_args = ["diff", "--unified=0", "--", filepath]
    if source == "staged":
        diff_args.insert(1, "--cached")
    diff_content = run_git(diff_args, check=False)
    added_lines = _extract_added_lines(diff_content)
    if added_lines:
        return added_lines
    if filepath not in untracked_files:
        return ""
    try:
        return Path(filepath).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def check_file_contents(files: list[str], *, source: str, untracked_files: set[str]) -> list[str]:
    """Scan candidate file contents for secret patterns."""
    violations: list[str] = []
    for filepath in files:
        try:
            diff_content = _read_candidate_content(
                filepath,
                source=source,
                untracked_files=untracked_files,
            )
            for pattern in CONTENT_PATTERNS:
                if pattern.search(diff_content):
                    violations.append(f"  🔍 CONTENT: {filepath} contains '{pattern.pattern}'")
                    break
        except (OSError, ValueError):
            pass  # Binary files or access errors — skip
    return violations


def main() -> int:
    files, source, untracked_files = get_candidate_files()
    if not files:
        return 0

    violations: list[str] = []
    violations.extend(check_filenames(files))
    violations.extend(check_file_contents(files, source=source, untracked_files=untracked_files))

    if violations:
        print(f"\n{RED}{BOLD}╔══════════════════════════════════════════════════╗{RESET}")
        print(f"{RED}{BOLD}║  🛑 SOVEREIGN SECURITY GATE — COMMIT BLOCKED    ║{RESET}")
        print(f"{RED}{BOLD}╚══════════════════════════════════════════════════╝{RESET}\n")
        scope = "staged files" if source == "staged" else "local diff files"
        print(f"{YELLOW}Wallet seeds / credentials detected in {scope}:{RESET}\n")
        for v in violations:
            print(f"{RED}{v}{RESET}")
        print(f"\n{YELLOW}If this is a false positive, bypass with:{RESET}")
        print("  git commit --no-verify\n")
        print(f"{RED}⚠️  Bots drain exposed wallet seeds in <600ms.{RESET}\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
