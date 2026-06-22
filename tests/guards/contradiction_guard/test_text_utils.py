import pytest
from cortex.guards.contradiction_guard.text_utils import (
    _tokenize,
    _jaccard,
    _detect_negation,
    _detect_supersession,
    _extract_versions,
    _is_noise,
    _decrypt_content,
    _embedding_cosine_similarity,
)


def test_tokenize():
    # Should ignore stop words and punctuation, returning sets of length >= 3
    text = "The quick brown fox jumps over the lazy dog."
    tokens = _tokenize(text)
    assert "quick" in tokens
    assert "brown" in tokens
    assert "fox" in tokens
    assert "the" not in tokens  # Stop word
    assert "jumps" in tokens

    # Test accents
    tokens_es = _tokenize("El niño corrió rápido.")
    assert "niño" in tokens_es
    assert "corrió" in tokens_es
    assert "rápido" in tokens_es


def test_jaccard():
    a = {"apple", "banana", "cherry"}
    b = {"banana", "cherry", "date"}
    assert _jaccard(a, b) == 2 / 4

    assert _jaccard(a, a) == 1.0
    assert _jaccard(a, set()) == 0.0
    assert _jaccard(set(), b) == 0.0
    assert _jaccard(set(), set()) == 0.0


def test_detect_negation():
    assert _detect_negation("This feature is forbidden in production.")
    assert _detect_negation("no usar este método")
    assert not _detect_negation("We should totally use this feature.")


def test_detect_supersession():
    assert _detect_supersession("This module supersedes the old one.")
    assert _detect_supersession("We replaced it yesterday.")
    assert not _detect_supersession("This is a brand new feature.")


def test_extract_versions():
    assert _extract_versions("Initial release v1.0 and update V2.1.3.") == ["1.0", "2.1.3"]
    assert _extract_versions("No versions here.") == []


def test_is_noise():
    assert _is_noise("MAILTV-1: ARCHIVE some text here")
    assert not _is_noise("Normal decision text")


def test_decrypt_content():
    def mock_decrypt(x):
        if x == "v6_aesgcm:valid":
            return "decrypted valid"
        raise ValueError("Invalid")

    assert _decrypt_content("plaintext", mock_decrypt) == "plaintext"
    assert _decrypt_content("v6_aesgcm:valid", mock_decrypt) == "decrypted valid"
    assert _decrypt_content("v6_aesgcm:invalid", mock_decrypt) is None
    assert _decrypt_content("v6_aesgcm:valid", None) == "v6_aesgcm:valid"


def test_embedding_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]

    assert _embedding_cosine_similarity(v1, v2) == pytest.approx(1.0)
    assert _embedding_cosine_similarity(v1, v3) == pytest.approx(0.0)
    assert _embedding_cosine_similarity(None, v1) == 0.0
    assert _embedding_cosine_similarity(v1, None) == 0.0
    assert _embedding_cosine_similarity(None, None) == 0.0
