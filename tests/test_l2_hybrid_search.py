"""Tests for cortex.memory.l2_hybrid_search — RRF fusion, FTS sanitizer, result model.

All tests exercise pure/static functions — no DB, no sqlite-vec required.
"""

from __future__ import annotations

from cortex.memory.l2_hybrid_search import (
    L2HybridSearch,
    L2SearchResult,
    _sanitize_fts_query,
)

# ─── _sanitize_fts_query ────────────────────────────────────────────────


class TestSanitizeFtsQuery:
    """Tests for FTS5 query sanitization."""

    def test_empty_string(self):
        assert _sanitize_fts_query("") == '""'

    def test_whitespace_only(self):
        assert _sanitize_fts_query("   ") == '""'

    def test_single_token_prefix_search(self):
        result = _sanitize_fts_query("hello")
        assert result == '"hello"*'

    def test_multi_token_and_join(self):
        result = _sanitize_fts_query("hello world")
        assert result == '"hello" AND "world"'

    def test_unsafe_chars_stripped(self):
        result = _sanitize_fts_query('test(foo) [bar] "baz"')
        # Parentheses, brackets, quotes stripped → tokens joined
        assert "(" not in result
        assert "[" not in result
        assert result.count("AND") >= 1

    def test_special_chars_only(self):
        result = _sanitize_fts_query("***^^^")
        # All chars stripped → empty
        assert result == '""'

    def test_mixed_safe_and_unsafe(self):
        result = _sanitize_fts_query("cortex:memory -> architecture")
        # Colons stripped, arrows stripped
        assert '"cortex"' in result or '"memory"' in result


# ─── L2HybridSearch._rrf_fuse ───────────────────────────────────────────


class TestRRFFuse:
    """Tests for the static RRF fusion method."""

    def test_empty_inputs(self):
        result = L2HybridSearch._rrf_fuse([], [], 0.6, 0.4, 5)
        assert result == []

    def test_vector_only(self):
        vec = [("id_a", 0), ("id_b", 1)]
        result = L2HybridSearch._rrf_fuse(vec, [], 0.6, 0.4, 5)
        assert len(result) == 2
        assert result[0][0] == "id_a"  # rank 0 → highest score
        assert result[0][1] > result[1][1]  # scores descending

    def test_fts_only(self):
        fts = [("id_x", 0), ("id_y", 1)]
        result = L2HybridSearch._rrf_fuse([], fts, 0.6, 0.4, 5)
        assert len(result) == 2
        assert result[0][0] == "id_x"

    def test_overlap_boosts_score(self):
        vec = [("shared", 0), ("vec_only", 1)]
        fts = [("shared", 0), ("fts_only", 1)]

        result = L2HybridSearch._rrf_fuse(vec, fts, 0.6, 0.4, 5)
        # "shared" appears in both → highest combined score
        assert result[0][0] == "shared"
        # Both signals should be present
        assert "vector" in result[0][2]
        assert "fts" in result[0][2]

    def test_top_k_limits_output(self):
        vec = [(f"v{i}", i) for i in range(20)]
        result = L2HybridSearch._rrf_fuse(vec, [], 0.6, 0.4, 3)
        assert len(result) == 3

    def test_signals_tracked(self):
        vec = [("a", 0)]
        fts = [("b", 0)]
        result = L2HybridSearch._rrf_fuse(vec, fts, 0.6, 0.4, 5)

        signal_map = {r[0]: r[2] for r in result}
        assert "vector" in signal_map["a"]
        assert "fts" in signal_map["b"]

    def test_weight_normalization(self):
        """Weights should be normalized — different absolute weights, same ratio, same results."""
        vec = [("a", 0), ("b", 1)]
        fts = [("c", 0)]

        r1 = L2HybridSearch._rrf_fuse(vec, fts, 0.6, 0.4, 5)
        r2 = L2HybridSearch._rrf_fuse(vec, fts, 6.0, 4.0, 5)

        # Same ID ordering
        assert [x[0] for x in r1] == [x[0] for x in r2]
        # Same scores (within float tolerance)
        for a, b in zip(r1, r2):
            assert abs(a[1] - b[1]) < 1e-10


# ─── L2SearchResult ──────────────────────────────────────────────────────


class TestL2SearchResult:
    """Tests for the L2SearchResult dataclass."""

    def _make_result(self, **kwargs):
        defaults = {
            "rank_index": 0,
            "internal_id": "abc123",
            "tenant_id": "t1",
            "project_id": "p1",
            "content": "test",
            "timestamp": 1710000000.0,
            "is_diamond": False,
            "is_bridge": False,
            "confidence": "C4",
            "cognitive_layer": "semantic",
            "rrf_score": 0.5,
            "source_signals": ["vector"],
        }
        defaults.update(kwargs)
        return L2SearchResult(**defaults)

    def test_to_context_dict_uses_rank_index(self):
        r = self._make_result(rank_index=3, internal_id="secret_uuid")
        d = r.to_context_dict()
        assert d["idx"] == 3
        assert "secret_uuid" not in str(d)

    def test_context_dict_score_rounded(self):
        r = self._make_result(rrf_score=0.123456789)
        d = r.to_context_dict()
        assert d["score"] == round(0.123456789, 6)

    def test_diamond_flag_in_context(self):
        r = self._make_result(is_diamond=True)
        d = r.to_context_dict()
        assert d["diamond"] is True

    def test_signals_preserved(self):
        r = self._make_result(source_signals=["vector", "fts"])
        d = r.to_context_dict()
        assert d["signals"] == ["vector", "fts"]
