"""Unit tests for consensus scoring algorithms.

Tests the scoring logic in ConsensusManager without requiring a DB or API.
Tests use a minimal mock engine to exercise _recalculate_consensus and
_recalculate_consensus_v2 scoring math.
"""

from __future__ import annotations

import pytest

from cortex.consensus.manager import (
    DISPUTED_THRESHOLD,
    SCORE_BASELINE,
    SCORE_CEILING,
    SCORE_FLOOR,
    V1_VOTE_WEIGHT,
    VERIFIED_THRESHOLD,
    ConsensusManager,
)

# ─── Helpers ─────────────────────────────────────────────────────────


class FakeConn:
    """Minimal mock for aiosqlite.Connection that returns canned rows."""

    def __init__(self, rows: list):
        self._rows = rows
        self.last_update: tuple | None = None

    async def execute(self, sql: str, params=None):
        if sql.strip().upper().startswith("UPDATE"):
            self.last_update = (sql, params)
            return self
        return FakeCursor(self._rows)


class FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    async def fetchone(self):
        return self._rows[0] if self._rows else None

    async def fetchall(self):
        return self._rows


class FakeEngine:
    """Stub engine to satisfy ConsensusManager constructor."""

    async def get_conn(self):
        return None

    async def log_transaction(self, conn, project, action, detail):
        return 1


# ─── V1 Scoring ──────────────────────────────────────────────────────


class TestV1Scoring:
    @pytest.mark.asyncio
    async def test_single_upvote(self):
        mgr = ConsensusManager(FakeEngine())
        conn = FakeConn([(1,)])  # SUM(vote) = 1
        score = await mgr._recalculate_consensus(1, conn)
        assert score == pytest.approx(SCORE_BASELINE + V1_VOTE_WEIGHT)

    @pytest.mark.asyncio
    async def test_single_downvote(self):
        mgr = ConsensusManager(FakeEngine())
        conn = FakeConn([(-1,)])  # SUM(vote) = -1
        score = await mgr._recalculate_consensus(1, conn)
        assert score == pytest.approx(SCORE_BASELINE - V1_VOTE_WEIGHT)

    @pytest.mark.asyncio
    async def test_no_votes(self):
        mgr = ConsensusManager(FakeEngine())
        conn = FakeConn([(None,)])
        score = await mgr._recalculate_consensus(1, conn)
        assert score == pytest.approx(SCORE_BASELINE)

    @pytest.mark.asyncio
    async def test_upper_clamp(self):
        """100 upvotes should be clamped to SCORE_CEILING."""
        mgr = ConsensusManager(FakeEngine())
        conn = FakeConn([(100,)])
        score = await mgr._recalculate_consensus(1, conn)
        assert score == SCORE_CEILING

    @pytest.mark.asyncio
    async def test_lower_clamp(self):
        """100 downvotes should be clamped to SCORE_FLOOR."""
        mgr = ConsensusManager(FakeEngine())
        conn = FakeConn([(-100,)])
        score = await mgr._recalculate_consensus(1, conn)
        assert score == SCORE_FLOOR


# ─── V2 Scoring ──────────────────────────────────────────────────────


class TestV2Scoring:
    @pytest.mark.asyncio
    async def test_whale_vs_shrimp(self):
        """Whale (rep=10) upvotes, shrimp (rep=1) downvotes → score > 1.0."""
        mgr = ConsensusManager(FakeEngine())
        # (vote, vote_weight, reputation_score)
        rows = [
            (1, 10.0, 10.0),   # whale upvotes
            (-1, 1.0, 1.0),    # shrimp downvotes
        ]
        conn = FakeConn(rows)
        score = await mgr._recalculate_consensus_v2(1, conn)
        # weighted_sum = 1*10 + (-1)*1 = 9, total_weight = 10+1 = 11
        # score = 1.0 + 9/11 ≈ 1.818
        assert score > 1.0
        assert score == pytest.approx(1.0 + 9.0 / 11.0)

    @pytest.mark.asyncio
    async def test_unanimous_upvote(self):
        mgr = ConsensusManager(FakeEngine())
        rows = [
            (1, 5.0, 5.0),
            (1, 3.0, 3.0),
        ]
        conn = FakeConn(rows)
        score = await mgr._recalculate_consensus_v2(1, conn)
        assert score == SCORE_CEILING

    @pytest.mark.asyncio
    async def test_unanimous_downvote(self):
        mgr = ConsensusManager(FakeEngine())
        rows = [
            (-1, 5.0, 5.0),
            (-1, 3.0, 3.0),
        ]
        conn = FakeConn(rows)
        score = await mgr._recalculate_consensus_v2(1, conn)
        assert score == SCORE_FLOOR

    @pytest.mark.asyncio
    async def test_no_v2_votes_falls_back_to_v1(self):
        """If no v2 votes exist, should fall back to v1 scoring."""
        mgr = ConsensusManager(FakeEngine())
        # v2 query returns no rows → falls back to v1
        # v1 query returns SUM=2
        call_count = 0

        class DualConn(FakeConn):
            def __init__(self):
                super().__init__([])

            async def execute(self, sql, params=None):
                nonlocal call_count
                call_count += 1
                if sql.strip().upper().startswith("UPDATE"):
                    return self
                if call_count == 1:
                    # First call: v2 query → no rows
                    return FakeCursor([])
                # Second call: v1 SUM query
                return FakeCursor([(2,)])

        conn = DualConn()
        score = await mgr._recalculate_consensus_v2(1, conn)
        assert score == pytest.approx(1.0 + 2 * V1_VOTE_WEIGHT)


# ─── Update Fact Score Thresholds ─────────────────────────────────────


class TestUpdateFactScore:
    @pytest.mark.asyncio
    async def test_verified_threshold(self):
        mgr = ConsensusManager(FakeEngine())
        conn = FakeConn([])
        await mgr._update_fact_score(1, VERIFIED_THRESHOLD, conn)
        assert conn.last_update is not None
        sql, params = conn.last_update
        assert params == (VERIFIED_THRESHOLD, "verified", 1)

    @pytest.mark.asyncio
    async def test_disputed_threshold(self):
        mgr = ConsensusManager(FakeEngine())
        conn = FakeConn([])
        await mgr._update_fact_score(1, DISPUTED_THRESHOLD, conn)
        assert conn.last_update is not None
        sql, params = conn.last_update
        assert params == (DISPUTED_THRESHOLD, "disputed", 1)

    @pytest.mark.asyncio
    async def test_neutral_no_confidence(self):
        mgr = ConsensusManager(FakeEngine())
        conn = FakeConn([])
        await mgr._update_fact_score(1, 1.0, conn)
        assert conn.last_update is not None
        sql, params = conn.last_update
        # Should NOT set confidence
        assert params == (1.0, 1)
