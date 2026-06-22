import pytest
from unittest.mock import MagicMock
from cortex.guards.contradiction_guard.scoring import (
    _classify_conflict,
    _score_candidate,
    EMBEDDING_BOOST_WEIGHT,
)


def test_classify_conflict_keyword():
    ctype, score = _classify_conflict(
        "Normal text", "Other normal text", {"normal"}, {"normal"}, 0.5
    )
    assert ctype == "keyword_overlap"
    assert score == 0.5


def test_classify_conflict_negation():
    ctype, score = _classify_conflict(
        "Normal text", "This is forbidden text", {"normal"}, {"forbidden"}, 0.5
    )
    assert ctype == "negation"
    assert score == 0.5 * 1.5


def test_classify_conflict_supersede():
    ctype, score = _classify_conflict(
        "This supersedes the old one", "Old one", {"supersedes"}, {"old"}, 0.5
    )
    assert ctype == "version_supersede"
    assert score == 0.5 * 1.2


def test_classify_conflict_version_supersede_with_versions():
    ctype, score = _classify_conflict(
        "Update to v2.0",
        "This is v1.0",
        {"update", "token1", "token2", "token3", "token4", "token5", "token6"},
        {"token1", "token2", "token3", "token4", "token5", "token6", "old"},
        0.5,
    )
    assert ctype == "version_supersede"
    assert score == 0.5 * 1.4


def test_score_candidate_none_cases():
    mock_row = {"content": "MAILTV-1: ARCHIVE ignored"}
    # should ignore noise
    assert _score_candidate(mock_row, {"test"}, "test content", "proj", None, 0.1) is None

    mock_row = {"content": "v6_aesgcm:invalid"}

    def mock_decrypt(x):
        raise ValueError()

    # should handle decryption failure (returns None content -> returns None)
    assert _score_candidate(mock_row, {"test"}, "test content", "proj", mock_decrypt, 0.1) is None

    mock_row = {
        "content": "This has completely different words",
        "project": "proj",
        "id": 1,
        "created_at": "2023-01-01",
    }
    # score below threshold
    assert (
        _score_candidate(mock_row, {"unique", "words"}, "unique words content", "proj", None, 0.99)
        is None
    )


def test_score_candidate_success():
    mock_row = {
        "content": "This is a matching project content.",
        "project": "TestProject",
        "id": 42,
        "created_at": "2023-05-10",
    }

    # same project boosts by 1.3
    # basic score will be high because of "matching", "project", "content" overlap
    tokens = {"matching", "project", "content"}

    candidate = _score_candidate(
        mock_row, tokens, "matching project content", "TestProject", None, 0.1
    )
    assert candidate is not None
    assert candidate.fact_id == 42
    assert candidate.project == "TestProject"
    assert candidate.overlap_score > 0.1


def test_score_candidate_embedding_boost():
    mock_row = {
        "content": "Apple banana cherry.",
        "project": "Proj1",
        "id": 1,
        "created_at": "2023-01-01",
    }

    # very high cosine similarity should boost and maybe set semantic_similarity if jaccard is low
    new_embedding = [1.0, 0.0]
    existing_embedding = [1.0, 0.0]

    candidate = _score_candidate(
        mock_row,
        {"dog", "cat"},  # completely disjoint tokens to keep jaccard low
        "Dog cat",
        "Proj1",
        None,
        0.1,
        new_embedding,
        existing_embedding,
    )

    assert candidate is not None
    assert candidate.conflict_type == "semantic_similarity"
    assert candidate.overlap_score == pytest.approx(min(EMBEDDING_BOOST_WEIGHT * 1.0, 1.0))
