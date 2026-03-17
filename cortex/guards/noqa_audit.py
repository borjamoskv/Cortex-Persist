"""
noqa_audit.py — The Systematic noqa:BLE001 Drift Detector.

Axiom: noqa:BLE001 is a signed promise. Un-reviewed promises become debt.

This module provides:
  - NoqaEntry: structured record of a single suppression
  - NoqaAudit: static scan + git archaeology engine
  - classify_entry(): quality scoring per entry

Usage (CLI): cortex guards noqa-report
Usage (CI):  check_gate_12_noqa_drift() in seals.py
Usage (monthly): cortex guards noqa-report --since="30 days ago"
"""

from __future__ import annotations
from typing import Optional

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

# ─── Data Model ───────────────────────────────────────────────────────────────


@dataclass
class NoqaEntry:
    """A single `# noqa: BLE001` suppression instance."""

    file: Path
    line_number: int
    line_content: str
    # Quality fields populated by classify_entry()
    has_justification: bool = False
    justification_text: str = ""
    # Git fields populated by enrich_with_git()
    introduced_commit: str = ""
    introduced_author: str = ""
    introduced_date: str = ""
    introduced_message: str = ""
    # Score: 0 (silent+old) → 3 (justified+recent)
    quality_score: int = 0

    @property
    def short_path(self) -> str:
        """Relative path for display."""
        try:
            return str(self.file.relative_to(self.file.parents[4]))
        except ValueError:
            return self.file.name

    @property
    def is_silent(self) -> bool:
        """True if the noqa has no explanatory comment on the same or next line."""
        return not self.has_justification


# ─── Classification ────────────────────────────────────────────────────────────

_JUSTIFICATION_PATTERNS = (
    r"—\s*.+",  # em-dash followed by reason
    r"-\s*[A-Z].+",  # dash + capital letter reason
    r"#\s*(deliberate|intentional|boundary|relay|supervisor|resilience|safety)",
)
_JUSTIFICATION_RE = re.compile("|".join(_JUSTIFICATION_PATTERNS), re.IGNORECASE)


def classify_entry(entry: NoqaEntry, next_line: str = "") -> NoqaEntry:
    """
    Score a NoqaEntry for justification quality.

    Score:
      0 — Silent noqa, no explanation anywhere
      1 — Has a next-line comment but no noqa-inline reason
      2 — Has an inline reason after the noqa marker
      3 — Has inline reason + descriptive next-line comment
    """
    inline_after_noqa = entry.line_content.split("# noqa: BLE001")[-1].strip()
    has_inline = bool(inline_after_noqa and _JUSTIFICATION_RE.search(inline_after_noqa))
    has_next = bool(next_line.strip().startswith("#") and len(next_line.strip()) > 5)

    entry.justification_text = inline_after_noqa or next_line.strip()
    entry.has_justification = has_inline or has_next
    entry.quality_score = sum([has_inline * 2, has_next * 1])
    return entry


# ─── Static Scanner ────────────────────────────────────────────────────────────


class NoqaAudit:
    """
    Scans the codebase for noqa:BLE001 suppressions and enriches with git data.
    """

    MARKERS = ("# noqa: BLE001", "# noqa:BLE001")

    def __init__(self, root: Path) -> None:
        self.root = root

    def scan(
        self,
        include_paths: Optional[list[str]] = None,
        exclude_paths: Optional[list[str]] = None,
    ) -> list[NoqaEntry]:
        """
        Static scan: find all noqa:BLE001 in the codebase.
        Returns list of NoqaEntry with quality classification.
        """
        exclude = set(
            exclude_paths
            or [
                "__pycache__",
                ".venv",
                "venv",
                ".git",
                "node_modules",
            ]
        )
        include = include_paths or ["cortex"]

        entries: list[NoqaEntry] = []

        for subdir in include:
            base = self.root / subdir
            if not base.exists():
                continue
            for py_file in base.rglob("*.py"):
                if any(ex in py_file.parts for ex in exclude):
                    continue
                entries.extend(self._scan_file(py_file))

        return entries

    def _scan_file(self, path: Path) -> list[NoqaEntry]:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            return []

        results = []
        for i, line in enumerate(lines):
            if any(marker in line for marker in self.MARKERS):
                candidate = NoqaEntry(
                    file=path,
                    line_number=i + 1,
                    line_content=line,
                )
                next_line = lines[i + 1] if i + 1 < len(lines) else ""
                classify_entry(candidate, next_line)
                results.append(candidate)
        return results

    def enrich_with_git(self, entries: list[NoqaEntry]) -> list[NoqaEntry]:
        """
        Use `git log -S` (pickaxe) per entry to find when each noqa was introduced.
        Expensive: runs one git command per unique file. Cached by file.
        """
        file_blame_cache: dict[Path, list[str]] = {}

        for entry in entries:
            if entry.file not in file_blame_cache:
                blame = self._git_blame_lines(entry.file)
                file_blame_cache[entry.file] = blame

            blame_lines = file_blame_cache[entry.file]
            if 0 < entry.line_number <= len(blame_lines):
                raw = blame_lines[entry.line_number - 1]
                self._parse_blame_line(entry, raw)

        return entries

    def _git_blame_lines(self, path: Path) -> list[str]:
        try:
            result = subprocess.run(
                ["git", "blame", "--porcelain", str(path)],
                cwd=self.root,
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )
            return result.stdout.splitlines()
        except (subprocess.SubprocessError, OSError):
            return []

    def _parse_blame_line(self, entry: NoqaEntry, raw: str) -> None:
        """Extract commit hash from porcelain blame line."""
        # Porcelain format: <40-char-hash> <orig-line> <final-line> <num-lines>
        parts = raw.split()
        if parts and len(parts[0]) == 40:
            entry.introduced_commit = parts[0][:8]

    def git_pickaxe(
        self,
        since: str = "30 days ago",
        search_term: str = "noqa: BLE001",
    ) -> list[dict[str, str]]:
        """
        `git log -S` to find all commits that introduced a noqa:BLE001.
        Returns list of {hash, date, author, subject} dicts.
        """
        try:
            result = subprocess.run(
                [
                    "git",
                    "log",
                    f"--since={since}",
                    f"-S{search_term}",
                    "--pretty=format:%H|%ad|%an|%s",
                    "--date=short",
                    "--diff-filter=A",  # Only commits that ADDED the pattern
                ],
                cwd=self.root,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            commits = []
            for line in result.stdout.splitlines():
                if "|" not in line:
                    continue
                parts = line.split("|", 3)
                if len(parts) == 4:
                    commits.append(
                        {
                            "hash": parts[0][:8],
                            "date": parts[1],
                            "author": parts[2],
                            "subject": parts[3],
                        }
                    )
            return commits
        except (subprocess.SubprocessError, OSError):
            return []


# ─── Report Formatting ─────────────────────────────────────────────────────────


def format_report(
    entries: list[NoqaEntry],
    git_commits: list[dict[str, str]],
    since: str = "30 days ago",
) -> str:
    """
    Produce a human-readable drift report.
    Returns the full report as a string for CLI display or CI output.
    """
    total = len(entries)
    silent = [e for e in entries if e.is_silent]
    justified = [e for e in entries if not e.is_silent]
    score_0 = [e for e in entries if e.quality_score == 0]

    lines = [
        "",
        "━" * 60,
        " 📋 noqa:BLE001 DRIFT REPORT — Sovereign Exception Audit",
        "━" * 60,
        f"  Total suppressions:     {total}",
        f"  ✅ Justified:           {len(justified)}",
        f"  ⚠️  Silent (score=0):    {len(score_0)}",
        f"  🔴 Unjustified:         {len(silent)}",
        "",
    ]

    # Git archaeology section
    lines.append(f"─ Git Pickaxe — New noqa:BLE001 since '{since}' ─")
    if git_commits:
        for c in git_commits:
            lines.append(f"  [{c['hash']}] {c['date']} {c['author']:<20} {c['subject']}")
    else:
        lines.append("  ✅  No new noqa:BLE001 introduced in this window.")
    lines.append("")

    # Silent entries (need justification)
    if score_0:
        lines.append("─ Silent suppressions (require justification) ─")
        for e in score_0:
            lines.append(f"  🔴 {e.short_path}:{e.line_number}")
            lines.append(f"     {e.line_content.strip()}")
        lines.append("")

    # Low-quality justified (inline reason only, no comment)
    score_1 = [e for e in entries if e.quality_score == 1]
    if score_1:
        lines.append("─ Partially justified (add inline reason) ─")
        for e in score_1:
            lines.append(f"  🟡 {e.short_path}:{e.line_number}")
        lines.append("")

    # Well-justified
    if justified and not score_0:
        lines.append("─ Fully justified suppressions ─")
        for e in justified:
            short_just = e.justification_text[:60].strip()
            lines.append(f"  ✅ {e.short_path}:{e.line_number} — {short_just}")
        lines.append("")

    lines.append("─ Verdict ─")
    if not silent and not git_commits:
        lines.append("  🟢 CLEAN — No drift detected. All suppressions are justified.")
    elif git_commits and not silent:
        lines.append(
            f"  🟡 DRIFT — {len(git_commits)} new noqa(s) introduced. All have justifications."
        )
    else:
        lines.append(
            f"  🔴 ACTION REQUIRED — {len(silent)} silent suppressions detected. "
            f"Add justification comments."
        )

    lines.append("━" * 60)
    return "\n".join(lines)


def drift_score(entries: list[NoqaEntry], new_commits: list[dict]) -> int:
    """
    Numeric drift score for CI gate thresholds.
    0 = perfect. >threshold = gate failure.
    -1 per unjustified entry, -2 per new commit without covered justification.
    """
    score = 0
    score -= sum(1 for e in entries if e.quality_score == 0)
    score -= len(new_commits) * 2
    return score
