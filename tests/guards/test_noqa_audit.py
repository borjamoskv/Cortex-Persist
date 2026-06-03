import pytest
from pathlib import Path
from cortex.guards.noqa_audit import (
    NoqaEntry,
    classify_entry,
    format_report,
    drift_score,
)

def test_classify_entry_happy():
    """Happy path: High quality score for good justifications."""
    entry = NoqaEntry(Path("file.py"), 1, "def f(): # noqa: BLE001 - intentional design")
    next_line = "# This is a detailed explanation of why we do this."

    result = classify_entry(entry, next_line)

    assert result.has_justification is True
    assert result.quality_score == 3
    assert "intentional design" in result.justification_text or "detailed explanation" in result.justification_text

def test_classify_entry_rejection():
    """Rejection path: Silent noqa gives score 0."""
    entry = NoqaEntry(Path("file.py"), 1, "def f(): # noqa: BLE001")
    next_line = "def g(): pass"

    result = classify_entry(entry, next_line)

    assert result.has_justification is False
    assert result.quality_score == 0

def test_classify_entry_boundary():
    """Boundary condition: Inline comment without strict pattern or next line that is short."""
    entry = NoqaEntry(Path("file.py"), 1, "def f(): # noqa: BLE001 whatever")
    next_line = "# short"

    result = classify_entry(entry, next_line)

    # Inline does not match regex (e.g. no dash), so it's 0. Next line is short (len <= 5 without strip), it strips to "# short" len 7, so it might be 1.
    # Actually "# short" len is 7, > 5. So it counts as next_line justification.
    assert result.quality_score == 1

    entry2 = NoqaEntry(Path("file.py"), 1, "def f(): # noqa: BLE001")
    next_line2 = "# foo" # len = 5, won't trigger next_line > 5
    result2 = classify_entry(entry2, next_line2)
    assert result2.quality_score == 0

def test_format_report_happy():
    """Happy path: Format a report with no silent entries and no new git commits."""
    entries = [
        NoqaEntry(Path("a/b/c/d/file.py"), 1, "def f(): # noqa: BLE001 - deliberate"),
    ]
    # Simulate classify
    entries[0].quality_score = 2
    entries[0].justification_text = "- deliberate"

    report = format_report(entries, [], "30 days ago")

    assert "Total suppressions:     1" in report
    assert "✅ Justified:           1" in report
    assert "CLEAN - No drift detected" in report

def test_format_report_rejection():
    """Rejection path: Format a report with silent entries and new commits."""
    entries = [
        NoqaEntry(Path("a/b/c/d/file.py"), 1, "def f(): # noqa: BLE001"),
    ]
    entries[0].quality_score = 0

    git_commits = [
        {"hash": "12345678", "date": "2026-01-01", "author": "Alice", "subject": "add bug"},
    ]

    report = format_report(entries, git_commits, "30 days ago")

    assert "Silent (score=0):    1" in report
    assert "ACTION REQUIRED - 1 silent suppressions" in report
    assert "12345678" in report

def test_format_report_boundary():
    """Boundary condition: Format a report with only score=1 entries."""
    entries = [
        NoqaEntry(Path("a/b/c/d/file.py"), 1, "def f(): # noqa: BLE001"),
    ]
    entries[0].quality_score = 1

    report = format_report(entries, [], "30 days ago")
    assert "Partially justified" in report

def test_drift_score_happy():
    """Happy path: 0 drift score for all justified and no new commits."""
    entries = [NoqaEntry(Path("file.py"), 1, "def f(): # noqa: BLE001")]
    entries[0].quality_score = 2
    assert drift_score(entries, []) == 0

def test_drift_score_rejection():
    """Rejection path: negative score for silent and new commits."""
    entries = [NoqaEntry(Path("file.py"), 1, "def f(): # noqa: BLE001")]
    entries[0].quality_score = 0
    commits = [{"hash": "1"}]
    # -1 for silent, -2 for commit = -3
    assert drift_score(entries, commits) == -3

def test_drift_score_boundary():
    """Boundary condition: Empty lists."""
    assert drift_score([], []) == 0
