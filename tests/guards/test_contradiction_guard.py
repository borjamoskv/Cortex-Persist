import pytest
import aiosqlite
import json
from dataclasses import dataclass
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from cortex.guards.contradiction_guard import (
    ConflictReport,
    ConflictCandidate,
    _tokenize,
    _jaccard,
    _detect_negation,
    _detect_supersession,
    _extract_versions,
    _is_noise,
    _decrypt_content,
    _classify_conflict,
    _score_candidate,
    _fetch_decision_rows,
    detect_contradictions,
    scan_all_contradictions,
    _process_token_bucket,
    _compare_decisions,
    _prepare_decisions,
    _build_token_index,
)


def test_tokenize_happy():
    assert _tokenize("Hello world! this is a test") == {"hello", "world", "test"}


def test_tokenize_rejection():
    assert _tokenize("") == set()
    assert _tokenize("a") == set()


def test_tokenize_boundary():
    assert _tokenize("123 !@# ABC") == {"abc"}


def test_jaccard_happy():
    assert _jaccard({"a", "b"}, {"b", "c"}) == 1 / 3


def test_jaccard_rejection():
    assert _jaccard(set(), set()) == 0.0


def test_jaccard_boundary():
    assert _jaccard({"a", "b"}, {"c", "d"}) == 0.0


def test_detect_negation_happy():
    assert _detect_negation("this is explicitly forbidden") is True


def test_detect_negation_rejection():
    assert _detect_negation("this is allowed") is False


def test_detect_negation_boundary():
    assert _detect_negation("forbidden") is True


def test_detect_supersession_happy():
    assert _detect_supersession("this supersedes the old method") is True


def test_detect_supersession_rejection():
    assert _detect_supersession("this is a cool feature") is False


def test_detect_supersession_boundary():
    assert _detect_supersession("replaces") is True


def test_extract_versions_happy():
    assert _extract_versions("v1.2.3 and v4.5.6") == ["1.2.3", "4.5.6"]


def test_extract_versions_rejection():
    assert _extract_versions("no versions here") == []


def test_extract_versions_boundary():
    assert _extract_versions("v1.0.0") == ["1.0.0"]


def test_is_noise_happy():
    assert _is_noise("archive from 2020") is False


def test_is_noise_rejection():
    assert _is_noise("important decision") is False


def test_is_noise_boundary():
    assert _is_noise("MAILTV-1: ARCHIVE") is True


def test_decrypt_content_happy():
    def decrypt_fn(c):
        return c.replace("v6_aesgcm:", "")

    assert _decrypt_content("v6_aesgcm:secret", decrypt_fn) == "secret"


def test_decrypt_content_rejection():
    def decrypt_fn(c):
        raise ValueError("error")

    assert _decrypt_content("v6_aesgcm:secret", decrypt_fn) is None


def test_decrypt_content_boundary():
    assert _decrypt_content("plaintext", None) == "plaintext"


def test_classify_conflict_happy():
    # regular overlap
    c_type, score = _classify_conflict("new", "old", {"new"}, {"old"}, 0.5)
    assert c_type == "keyword_overlap"
    assert score == 0.5


def test_classify_conflict_rejection():
    # negation
    c_type, score = _classify_conflict("forbidden", "allowed", {"new"}, {"old"}, 0.5)
    assert c_type == "negation"
    assert score == 0.5 * 1.5


def test_classify_conflict_boundary():
    # supersession
    c_type, score = _classify_conflict("supersedes", "allowed", {"new"}, {"old"}, 0.5)
    assert c_type == "version_supersede"
    assert score == 0.5 * 1.2


def test_score_candidate_happy():
    row = {
        "content": "this is a test content",
        "project": "test",
        "topic": "test",
        "id": 1,
        "created_at": "2023-01-01T00:00:00",
    }
    new_tokens = {"test", "content"}
    candidate = _score_candidate(row, new_tokens, "test content", "test", None, 0.1)
    assert candidate is not None
    assert candidate.overlap_score > 0


def test_score_candidate_rejection():
    row = {
        "content": "MAILTV-1: ARCHIVE",
        "project": "test",
        "topic": "test",
        "id": 1,
        "created_at": "2023-01-01T00:00:00",
    }
    new_tokens = {"test", "content"}
    candidate = _score_candidate(row, new_tokens, "test content", "test", None, 0.1)
    assert candidate is None


def test_score_candidate_boundary():
    row = {
        "content": "different content entirely",
        "project": "test",
        "topic": "test",
        "id": 1,
        "created_at": "2023-01-01T00:00:00",
    }
    new_tokens = {"test", "content"}
    # The score should be 0, so if min_score is 0.5 it will return None
    candidate = _score_candidate(row, new_tokens, "test content", "test", None, 0.5)
    assert candidate is None


@pytest.mark.asyncio
async def test_fetch_decision_rows_happy():
    conn = AsyncMock()
    # To mock async iterator:
    conn.execute.return_value.fetchall = AsyncMock(return_value=[{"id": 1, "content": "test"}])
    rows = await _fetch_decision_rows(conn, {"test"}, "test_project", use_fts=False)
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_fetch_decision_rows_rejection():
    conn = AsyncMock()
    conn.execute.return_value.fetchall = AsyncMock(return_value=[])
    rows = await _fetch_decision_rows(conn, {"test"}, "test_project", use_fts=False)
    assert len(rows) == 0


@pytest.mark.asyncio
async def test_fetch_decision_rows_boundary():
    conn = AsyncMock()
    conn.execute.return_value.fetchall = AsyncMock(return_value=[{"id": 1}])
    rows = await _fetch_decision_rows(conn, {"test"}, "test_project", use_fts=False)
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_detect_contradictions_happy():
    with patch("cortex.guards.contradiction_guard.connect_async_ctx") as mock_ctx:
        conn = AsyncMock()
        conn.execute.return_value.fetchall = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "content": "we decided to use pytest",
                    "project": "cortex",
                    "created_at": "2023-01-01T00:00:00",
                }
            ]
        )
        mock_ctx.return_value.__aenter__.return_value = conn

        report = await detect_contradictions(
            new_content="we decided to use pytest", new_project="cortex", min_score=0.1
        )
        assert report.has_conflicts is True
        assert len(report.candidates) == 1
        assert report.candidates[0].overlap_score > 0


@pytest.mark.asyncio
async def test_detect_contradictions_rejection():
    with patch("cortex.guards.contradiction_guard.connect_async_ctx") as mock_ctx:
        conn = AsyncMock()
        conn.execute.return_value.fetchall = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "content": "completely unrelated content",
                    "project": "cortex",
                    "created_at": "2023-01-01T00:00:00",
                }
            ]
        )
        mock_ctx.return_value.__aenter__.return_value = conn

        report = await detect_contradictions(
            new_content="we decided to use pytest", new_project="cortex", min_score=0.9
        )
        assert report.has_conflicts is False
        assert len(report.candidates) == 0


@pytest.mark.asyncio
async def test_detect_contradictions_boundary():
    with patch("cortex.guards.contradiction_guard.connect_async_ctx") as mock_ctx:
        conn = AsyncMock()
        conn.execute.return_value.fetchall = AsyncMock(return_value=[])
        mock_ctx.return_value.__aenter__.return_value = conn

        report = await detect_contradictions(
            new_content="we decided to use pytest", new_project="cortex", min_score=0.1
        )
        assert report.has_conflicts is False


@pytest.mark.asyncio
async def test_scan_all_contradictions_happy():
    with patch("cortex.guards.contradiction_guard.connect_async_ctx") as mock_ctx:
        conn = AsyncMock()
        conn.execute.return_value.fetchall = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "content": "we decided to use pytest",
                    "project": "cortex",
                    "created_at": "2023-01-01T00:00:00",
                },
                {
                    "id": 2,
                    "content": "we are using pytest exclusively",
                    "project": "cortex",
                    "created_at": "2023-01-02T00:00:00",
                },
            ]
        )
        mock_ctx.return_value.__aenter__.return_value = conn

        candidates = await scan_all_contradictions(min_score=0.1)
        assert len(candidates) > 0


@pytest.mark.asyncio
async def test_scan_all_contradictions_rejection():
    with patch("cortex.guards.contradiction_guard.connect_async_ctx") as mock_ctx:
        conn = AsyncMock()
        conn.execute.return_value.fetchall = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "content": "we decided to use pytest",
                    "project": "cortex",
                    "created_at": "2023-01-01T00:00:00",
                },
                {
                    "id": 2,
                    "content": "completely different decision",
                    "project": "cortex",
                    "created_at": "2023-01-02T00:00:00",
                },
            ]
        )
        mock_ctx.return_value.__aenter__.return_value = conn

        candidates = await scan_all_contradictions(min_score=0.9)
        # Assuming completely different text shouldn't exceed min_score (e.g. 0.9)
        assert len(candidates) == 0


@pytest.mark.asyncio
async def test_scan_all_contradictions_boundary():
    with patch("cortex.guards.contradiction_guard.connect_async_ctx") as mock_ctx:
        conn = AsyncMock()
        conn.execute.return_value.fetchall = AsyncMock(return_value=[])
        mock_ctx.return_value.__aenter__.return_value = conn

        candidates = await scan_all_contradictions()
        assert len(candidates) == 0


@pytest.mark.asyncio
async def test_detect_contradictions_no_tokens():
    report = await detect_contradictions(new_content="hi", new_project="cortex")
    assert report.has_conflicts is False


@pytest.mark.asyncio
async def test_detect_contradictions_is_noise():
    report = await detect_contradictions(new_content="MAILTV-1: ARCHIVE", new_project="cortex")
    assert report.has_conflicts is False


def test_conflict_candidate_format():
    candidate = ConflictCandidate(
        fact_id=1,
        project="cortex",
        content="test content",
        date="2023-01-01",
        overlap_score=0.5,
        conflict_type="keyword_overlap",
    )
    assert "cortex" in str(candidate)


def test_conflict_report_severity():
    report = ConflictReport("test", "test")
    report.candidates = []
    assert report.severity == "clean"

    report.candidates = [ConflictCandidate(1, "test", "test", "2023", 0.9, "keyword_overlap")]
    assert report.severity == "high"

    report.candidates = [ConflictCandidate(1, "test", "test", "2023", 0.6, "keyword_overlap")]
    assert report.severity == "high"

    report.candidates = [ConflictCandidate(1, "test", "test", "2023", 0.4, "keyword_overlap")]
    assert report.severity == "medium"


def test_conflict_report_format():
    report = ConflictReport("test", "test")
    assert report.format() == "✅ No contradictions detected."

    report.candidates = [ConflictCandidate(1, "test", "test", "2023", 0.9, "keyword_overlap")]
    formatted = report.format()
    assert "potential contradiction" in formatted
    assert "high" in formatted


def test_process_token_bucket_happy():
    group = [
        {
            "id": 1,
            "tokens": {"test", "content"},
            "content": "test content",
            "date": "2023",
            "project": "p",
        },
        {
            "id": 2,
            "tokens": {"test", "content"},
            "content": "test content",
            "date": "2023",
            "project": "p",
        },
    ]
    indices = [0, 1]
    pairs = []
    seen_pairs = set()
    _process_token_bucket(indices, group, seen_pairs, pairs, 0.1)
    assert len(pairs) == 1


def test_compare_decisions_happy():
    a = {
        "id": 1,
        "tokens": {"test", "content"},
        "content": "test content",
        "date": "2023",
        "project": "p",
    }
    b = {
        "id": 2,
        "tokens": {"test", "content"},
        "content": "test content",
        "date": "2023",
        "project": "p",
    }
    result = _compare_decisions(a, b, 0.1)
    assert result is not None


def test_compare_decisions_rejection():
    a = {
        "id": 1,
        "tokens": {"test", "content"},
        "content": "test content",
        "date": "2023",
        "project": "p",
    }
    b = {
        "id": 2,
        "tokens": {"different", "thing"},
        "content": "different thing",
        "date": "2023",
        "project": "p",
    }
    result = _compare_decisions(a, b, 0.5)
    assert result is None


def test_compare_decisions_boundary():
    a = {
        "id": 1,
        "tokens": {"test", "content"},
        "content": "forbidden test",
        "date": "2023",
        "project": "p",
    }
    b = {
        "id": 2,
        "tokens": {"test", "content"},
        "content": "supersedes test",
        "date": "2023",
        "project": "p",
    }
    result = _compare_decisions(a, b, 0.1)
    assert result is not None
    assert result[1].conflict_type == "version_supersede"


def test_prepare_decisions_happy():
    rows = [
        {
            "id": 1,
            "content": "test content word another",
            "project": "p",
            "created_at": "2023-01-01",
        }
    ]
    decisions = _prepare_decisions(rows, None)
    assert len(decisions) == 1


def test_prepare_decisions_rejection():
    rows = [{"id": 1, "content": "MAILTV archive", "project": "p", "created_at": "2023-01-01"}]
    decisions = _prepare_decisions(rows, None)
    assert len(decisions) == 0


def test_prepare_decisions_boundary():
    rows = [{"id": 1, "content": "shrt", "project": "p", "created_at": "2023-01-01"}]
    decisions = _prepare_decisions(rows, None)
    assert len(decisions) == 0


def test_build_token_index_happy():
    group = [
        {
            "id": 1,
            "tokens": {"test", "content"},
            "content": "test content",
            "date": "2023",
            "project": "p",
        }
    ]
    index = _build_token_index(group)
    assert "test" in index
    assert "content" in index


def test_conflict_report_has_conflicts():
    report = ConflictReport("test", "test")
    report.candidates = []
    assert report.has_conflicts is False
    report.candidates = [ConflictCandidate(1, "test", "test", "2023", 0.9, "keyword_overlap")]
    assert report.has_conflicts is True


def test_conflict_candidate_str():
    candidate = ConflictCandidate(1, "cortex", "test content", "2023-01-01", 0.5, "keyword_overlap")
    assert "cortex" in str(candidate)
