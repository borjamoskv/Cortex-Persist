import pytest
from cortex.guards.contradiction_guard.models import ConflictCandidate, ConflictReport


def test_conflict_candidate_str():
    candidate = ConflictCandidate(
        fact_id=123,
        project="TestProject",
        content="This is a test content that is somewhat long.",
        date="2023-10-27",
        overlap_score=0.85,
        conflict_type="keyword_overlap",
    )
    s = str(candidate)
    assert "[#123|TestProject|2023-10-27]" in s
    assert "(keyword_overlap, score=0.85)" in s
    assert "This is a test content that is somewhat long." in s


def test_conflict_report_no_candidates():
    report = ConflictReport(new_content="content", new_project="project")
    assert not report.has_conflicts
    assert report.severity == "clean"
    assert report.format() == "✅ No contradictions detected."


def test_conflict_report_with_candidates():
    c1 = ConflictCandidate(1, "p", "c1", "d", 0.5, "t")
    c2 = ConflictCandidate(2, "p", "c2", "d", 0.7, "t")
    report = ConflictReport(new_content="content", new_project="project", candidates=[c1, c2])

    assert report.has_conflicts
    assert report.severity == "high"  # max is 0.7 >= 0.6

    fmt = report.format()
    assert "⚠️ 2 potential contradiction(s) (severity: high):" in fmt
    assert str(c2) in fmt
    assert str(c1) in fmt
    assert "ACTION REQUIRED" in fmt


def test_conflict_report_severity_medium():
    c1 = ConflictCandidate(1, "p", "c1", "d", 0.45, "t")
    report = ConflictReport(new_content="content", new_project="project", candidates=[c1])
    assert report.severity == "medium"


def test_conflict_report_severity_low():
    c1 = ConflictCandidate(1, "p", "c1", "d", 0.2, "t")
    report = ConflictReport(new_content="content", new_project="project", candidates=[c1])
    assert report.severity == "low"
