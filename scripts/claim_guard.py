#!/usr/bin/env python3
"""claim_guard.py — CI gate that blocks banned compliance-overclaim terms.

Scans tracked source, docs, and marketing files for absolute legal claims
that have been designated P0 violations by the CORTEX compliance hardening
audit (session cd74333b).

Exit codes:
    0 — clean (no violations found)
    1 — violations found (CI must fail)
    2 — configuration / invocation error

Usage:
    python scripts/claim_guard.py                  # scan defaults
    python scripts/claim_guard.py --strict         # treat warnings as errors
    python scripts/claim_guard.py --path src/ docs/ cortex/
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Banned term registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BannedTerm:
    pattern: str          # regex pattern (case-insensitive)
    severity: str         # "error" | "warning"
    canonical: str        # replacement guidance
    rationale: str        # why this term is banned


BANNED: list[BannedTerm] = [
    # Absolute compliance verdicts ─────────────────────────────────────────
    BannedTerm(
        pattern=r"\bCOMPLIANT\b(?!\s*_CONTROLS_)",
        severity="error",
        canonical="SUPPORTIVE_CONTROLS_PRESENT / SUPPORTIVE_CONTROLS_PARTIAL",
        rationale="Binary compliance verdict creates legal liability; "
                  "CORTEX generates evidence controls, not certification.",
    ),
    BannedTerm(
        pattern=r"\bNON[_-]?COMPLIANT\b",
        severity="error",
        canonical="SUPPORTIVE_CONTROLS_MISSING",
        rationale="Binary non-compliance verdict creates liability.",
    ),
    BannedTerm(
        pattern=r"All Article 12 requirements met",
        severity="error",
        canonical=(
            "Technical evidence controls are present. "
            "Final compliance depends on legal/audit review."
        ),
        rationale="Absolute satisfaction claim is legally overclaiming.",
    ),
    BannedTerm(
        pattern=r"guarantees?\s+(compliance|regulatory\s+compliance)",
        severity="error",
        canonical="supports regulatory evidence generation",
        rationale="'Guarantees compliance' is an absolute legal claim.",
    ),
    BannedTerm(
        pattern=r"(?:ensures?|provides?|delivers?)\s+(?:full\s+)?compliance",
        severity="error",
        canonical="generates technical evidence controls",
        rationale="Absolute compliance assurance claim.",
    ),
    # Tamper-proof language ────────────────────────────────────────────────
    BannedTerm(
        pattern=r"\btamper[_-]?proof\b",
        severity="error",
        canonical="tamper-evident",
        rationale=(
            "Tamper-proof is an unverifiable absolute; "
            "tamper-evident accurately describes hash-chain integrity."
        ),
    ),
    # Stale penalty figures ────────────────────────────────────────────────
    BannedTerm(
        pattern=r"€\s*30\s*[Mm](?:illion)?",
        severity="error",
        canonical="€35M (7% of global annual turnover)",
        rationale="Stale EU AI Act Tier 1 penalty figure post-7 May 2026.",
    ),
    BannedTerm(
        pattern=r"6\s*%\s*(?:of\s+)?(?:global\s+)?(?:annual\s+)?turnover",
        severity="error",
        canonical="7% of global annual turnover",
        rationale="Stale EU AI Act Tier 1 percentage post-7 May 2026.",
    ),
    # Hyperbolic marketing claims ──────────────────────────────────────────
    BannedTerm(
        pattern=r"native(?:ly)?\s+(?:GDPR|EU\s*AI\s*Act)",
        severity="warning",
        canonical="supports GDPR/EU AI Act evidence generation",
        rationale="'Natively compliant' frames CORTEX as a certifier.",
    ),
    BannedTerm(
        pattern=r"intercepts?\s+hallucinations?\s+in\s+\d",
        severity="warning",
        canonical=(
            "detects factual drift via hash-chain comparison "
            "(latency varies by deployment)"
        ),
        rationale="Specific sub-millisecond latency claim is unverifiable.",
    ),
    BannedTerm(
        pattern=r"(?:resolves?|solves?)\s+compliance\s+natively",
        severity="error",
        canonical="generates evidence controls to support compliance review",
        rationale="'Solves compliance natively' is an absolute legal overclaim.",
    ),
    BannedTerm(
        pattern=r"GDPR\s+nativ[oe]",
        severity="error",
        canonical="GDPR-supportive evidence controls",
        rationale="'GDPR nativo' implies legal certification, not technical support.",
    ),
]

# ---------------------------------------------------------------------------
# File scope
# ---------------------------------------------------------------------------

DEFAULT_PATHS: list[str] = [
    "cortex/",
    "docs/",
    "src/",
    "README.md",
    "CHANGELOG.md",
]

INCLUDE_EXTENSIONS: set[str] = {
    ".py", ".md", ".rst", ".html", ".astro", ".txt", ".json", ".yaml", ".yml",
}

EXCLUDE_DIRS: set[str] = {
    "__pycache__", ".git", ".mypy_cache", ".ruff_cache",
    "node_modules", ".venv", "venv", ".tox", "dist", "build",
}

# This file itself + its test must be excluded from scanning
EXCLUDE_FILES: set[str] = {
    "claim_guard.py",
    "test_claim_guard.py",
}


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

@dataclass
class Violation:
    file: Path
    line_no: int
    line: str
    term: BannedTerm
    match: str


def _collect_files(paths: list[str], root: Path) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        target = root / p
        if target.is_file():
            if target.suffix in INCLUDE_EXTENSIONS and target.name not in EXCLUDE_FILES:
                files.append(target)
        elif target.is_dir():
            for f in target.rglob("*"):
                if (
                    f.is_file()
                    and f.suffix in INCLUDE_EXTENSIONS
                    and f.name not in EXCLUDE_FILES
                    and not any(part in EXCLUDE_DIRS for part in f.parts)
                ):
                    files.append(f)
    return sorted(set(files))


def scan(paths: list[str], root: Path) -> list[Violation]:
    violations: list[Violation] = []
    compiled = [
        (term, re.compile(term.pattern, re.IGNORECASE)) for term in BANNED
    ]
    for fpath in _collect_files(paths, root):
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for term, rx in compiled:
                m = rx.search(line)
                if m:
                    violations.append(
                        Violation(
                            file=fpath,
                            line_no=lineno,
                            line=line.strip(),
                            term=term,
                            match=m.group(0),
                        )
                    )
    return violations


def report(violations: list[Violation], *, strict: bool) -> int:
    """Print violations and return exit code."""
    errors = [v for v in violations if v.term.severity == "error"]
    warnings = [v for v in violations if v.term.severity == "warning"]

    if not violations:
        print("✅  claim_guard: no violations found — clean.")
        return 0

    for v in violations:
        badge = "❌ ERROR" if v.term.severity == "error" else "⚠️  WARN "
        print(
            f"{badge}  {v.file}:{v.line_no}\n"
            f"       match   : {v.match!r}\n"
            f"       line    : {v.line[:120]}\n"
            f"       rationale: {v.term.rationale}\n"
            f"       use     : {v.term.canonical}\n"
        )

    n_errors = len(errors)
    n_warns = len(warnings)
    print(
        f"\nclaim_guard summary: {n_errors} error(s), {n_warns} warning(s) "
        f"across {len({v.file for v in violations})} file(s)."
    )
    print(
        "  ⚠️  This guard enforces evidence-support language per the CORTEX "
        "compliance hardening audit (session cd74333b)."
    )

    if errors:
        return 1
    if strict and warnings:
        return 1
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "CORTEX Claim Guard — CI gate blocking compliance overclaims. "
            "Exits 1 on any error-level violation."
        )
    )
    parser.add_argument(
        "--path",
        nargs="+",
        default=DEFAULT_PATHS,
        help="Paths to scan (files or directories). Defaults to cortex/, docs/, src/.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (fail CI on any match).",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root. Defaults to current directory.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    violations = scan(args.path, root)
    sys.exit(report(violations, strict=args.strict))


if __name__ == "__main__":
    main()
