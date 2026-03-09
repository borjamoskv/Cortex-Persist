#!/usr/bin/env python3
"""
CORTEX Sovereign Pre-Commit Hook
=================================
Last line of defense against credential/seed leaks.
Catches what .gitignore cannot — including `git add -f`.

DERIVATION: Ω₃ Byzantine Default — verify, then trust.
"""
import subprocess
import sys
import re

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
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True,
        text=True,
    )
    return [f for f in result.stdout.strip().split("\n") if f]


def check_filenames(files: list[str]) -> list[str]:
    """Check staged filenames against forbidden patterns."""
    violations: list[str] = []
    for filepath in files:
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(filepath):
                violations.append(f"  🚫 FILENAME: {filepath} (matched: {pattern.pattern})")
                break
    return violations


def check_file_contents(files: list[str]) -> list[str]:
    """Scan staged file contents for secret patterns."""
    violations: list[str] = []
    for filepath in files:
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--", filepath],
                capture_output=True,
                text=True,
            )
            diff_content = result.stdout
            for pattern in CONTENT_PATTERNS:
                if pattern.search(diff_content):
                    violations.append(
                        f"  🔍 CONTENT: {filepath} contains '{pattern.pattern}'"
                    )
                    break
        except Exception:
            pass  # Binary files or access errors — skip
    return violations


def main() -> int:
    files = get_staged_files()
    if not files:
        return 0

    violations: list[str] = []
    violations.extend(check_filenames(files))
    violations.extend(check_file_contents(files))

    if violations:
        print(f"\n{RED}{BOLD}╔══════════════════════════════════════════════════╗{RESET}")
        print(f"{RED}{BOLD}║  🛑 SOVEREIGN SECURITY GATE — COMMIT BLOCKED    ║{RESET}")
        print(f"{RED}{BOLD}╚══════════════════════════════════════════════════╝{RESET}\n")
        print(f"{YELLOW}Wallet seeds / credentials detected in staged files:{RESET}\n")
        for v in violations:
            print(f"{RED}{v}{RESET}")
        print(f"\n{YELLOW}If this is a false positive, bypass with:{RESET}")
        print(f"  git commit --no-verify\n")
        print(f"{RED}⚠️  Bots drain exposed wallet seeds in <600ms.{RESET}\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
