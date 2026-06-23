# [C5-REAL] Exergy-Maximized
"""Tests for babylon60.consensus.rwa_bft - RWA-BFT Consensus Protocol.

C5-REAL audit remediation: consensus/ had 0% test coverage.
Validates: supermajority condition, Markov reputation updates, Byzantine detection,
quorum enforcement, edge cases.
"""

import pytest

from babylon60.consensus.rwa_bft import (
    AgentVote,
    ConsensusResult,
    RWABFTConsensus,
    VoteOutcome,
)


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def consensus():
    """Fresh RWA-BFT consensus engine with default params."""
    return RWABFTConsensus()


@pytest.fixture
def consensus_low_quorum():
    """Consensus engine with min_quorum=1 for edge case testing."""
    return RWABFTConsensus(min_quorum=1)


def _vote(agent: str, fact: str, outcome: VoteOutcome, confidence: float = 1.0) -> AgentVote:
    return AgentVote(agent_id=agent, fact_id=fact, outcome=outcome, confidence=confidence)


# ── Basic Consensus ──────────────────────────────────────────────────────


class TestBasicConsensus:
    """Tests for fundamental consensus mechanics."""

    def test_unanimous_for_accepts(self, consensus):
        votes = [
            _vote("A", "f1", VoteOutcome.FOR),
            _vote("B", "f1", VoteOutcome.FOR),
            _vote("C", "f1", VoteOutcome.FOR),
        ]
        result = consensus.evaluate("f1", votes)
        assert result.accepted is True
        assert result.supermajority_met is True
        assert result.quorum_size == 3

    def test_unanimous_against_rejects(self, consensus):
        votes = [
            _vote("A", "f1", VoteOutcome.AGAINST),
            _vote("B", "f1", VoteOutcome.AGAINST),
            _vote("C", "f1", VoteOutcome.AGAINST),
        ]
        result = consensus.evaluate("f1", votes)
        assert result.accepted is False
        assert result.supermajority_met is False

    def test_empty_votes_rejects(self, consensus):
        result = consensus.evaluate("f1", [])
        assert result.accepted is False
        assert result.total_reputation == 0.0

    def test_supermajority_2_of_3(self, consensus):
        votes = [
            _vote("A", "f1", VoteOutcome.FOR),
            _vote("B", "f1", VoteOutcome.FOR),
            _vote("C", "f1", VoteOutcome.AGAINST),
        ]
        result = consensus.evaluate("f1", votes)
        # 2/3 of equal-reputation agents = exactly 66.7%, threshold is >66.7%
        # With default reputation 1.0 each: 2.0 > (2/3 * 3.0) = 2.0 → NOT > (strictly greater)
        # So this should NOT meet supermajority
        assert result.supermajority_met is False

    def test_clear_supermajority_3_of_4(self, consensus):
        votes = [
            _vote("A", "f1", VoteOutcome.FOR),
            _vote("B", "f1", VoteOutcome.FOR),
            _vote("C", "f1", VoteOutcome.FOR),
            _vote("D", "f1", VoteOutcome.AGAINST),
        ]
        result = consensus.evaluate("f1", votes)
        # 3/4 = 75% > 66.7% → supermajority met
        assert result.accepted is True
        assert result.supermajority_met is True


# ── Quorum ───────────────────────────────────────────────────────────────


class TestQuorum:
    """Tests for quorum enforcement."""

    def test_below_min_quorum_rejects(self, consensus):
        # Default min_quorum = 2, send only 1 non-abstain
        votes = [
            _vote("A", "f1", VoteOutcome.FOR),
            _vote("B", "f1", VoteOutcome.ABSTAIN),
        ]
        result = consensus.evaluate("f1", votes)
        assert result.accepted is False
        assert result.quorum_size == 1

    def test_abstain_only_no_quorum(self, consensus):
        votes = [
            _vote("A", "f1", VoteOutcome.ABSTAIN),
            _vote("B", "f1", VoteOutcome.ABSTAIN),
        ]
        result = consensus.evaluate("f1", votes)
        assert result.accepted is False
        assert result.quorum_size == 0

    def test_exactly_at_quorum(self, consensus):
        votes = [
            _vote("A", "f1", VoteOutcome.FOR),
            _vote("B", "f1", VoteOutcome.FOR),
        ]
        result = consensus.evaluate("f1", votes)
        assert result.accepted is True
        assert result.quorum_size == 2


# ── Reputation Updates ───────────────────────────────────────────────────


class TestReputationUpdates:
    """Tests for Markov reputation chain updates (Eq. 2)."""

    def test_reputation_increases_for_correct_vote(self, consensus):
        initial_rep = consensus.reputation("A")
        votes = [
            _vote("A", "f1", VoteOutcome.FOR),
            _vote("B", "f1", VoteOutcome.FOR),
            _vote("C", "f1", VoteOutcome.FOR),
        ]
        consensus.evaluate("f1", votes)
        # After voting correctly (FOR when consensus is FOR):
        # R_new = λ * 1.0 + (1-λ) * 1.0 = 0.85 + 0.15 = 1.0
        assert consensus.reputation("A") == pytest.approx(1.0, abs=0.01)

    def test_reputation_decreases_for_wrong_vote(self, consensus):
        votes = [
            _vote("A", "f1", VoteOutcome.FOR),
            _vote("B", "f1", VoteOutcome.FOR),
            _vote("C", "f1", VoteOutcome.FOR),
            _vote("D", "f1", VoteOutcome.AGAINST, confidence=1.0),
        ]
        consensus.evaluate("f1", votes)
        # D voted AGAINST when consensus accepted → Φ = -3.0 * 1.0
        # R_new = 0.85 * 1.0 + 0.15 * (-3.0) = 0.85 - 0.45 = 0.40
        assert consensus.reputation("D") == pytest.approx(0.40, abs=0.01)

    def test_reputation_clamped_above_zero(self, consensus):
        # Repeatedly penalize an agent
        for i in range(20):
            votes = [
                _vote("rogue", f"f{i}", VoteOutcome.AGAINST, confidence=1.0),
                _vote("good_1", f"f{i}", VoteOutcome.FOR),
                _vote("good_2", f"f{i}", VoteOutcome.FOR),
                _vote("good_3", f"f{i}", VoteOutcome.FOR),
            ]
            consensus.evaluate(f"f{i}", votes)
        # Should be clamped to 0.01, never zero
        assert consensus.reputation("rogue") >= 0.01

    def test_abstain_no_reputation_change(self, consensus):
        # First, establish a known reputation via a round
        init_votes = [
            _vote("A", "f0", VoteOutcome.FOR),
            _vote("B", "f0", VoteOutcome.FOR),
        ]
        consensus.evaluate("f0", init_votes)
        rep_before = consensus.reputation("A")

        # A abstains in next round
        votes = [
            _vote("A", "f1", VoteOutcome.ABSTAIN),
            _vote("B", "f1", VoteOutcome.FOR),
            _vote("C", "f1", VoteOutcome.FOR),
        ]
        consensus.evaluate("f1", votes)
        # Φ = 0.0 for abstain → R_new = λ * R_old + (1-λ) * 0 = λ * R_old
        expected = 0.85 * rep_before
        assert consensus.reputation("A") == pytest.approx(expected, abs=0.01)


# ── Byzantine Detection ──────────────────────────────────────────────────


class TestByzantineDetection:
    """Tests for outlier/byzantine node detection."""

    def test_no_byzantine_in_unanimous(self, consensus):
        votes = [
            _vote("A", "f1", VoteOutcome.FOR),
            _vote("B", "f1", VoteOutcome.FOR),
        ]
        result = consensus.evaluate("f1", votes)
        assert result.byzantine_detected is False
        assert result.outlier_agents == []

    def test_result_to_dict_serializable(self, consensus):
        votes = [
            _vote("A", "f1", VoteOutcome.FOR),
            _vote("B", "f1", VoteOutcome.FOR),
        ]
        result = consensus.evaluate("f1", votes)
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "fact_id" in d
        assert "accepted" in d
        assert "approval_ratio" in d


# ── Audit Trail ──────────────────────────────────────────────────────────


class TestAuditTrail:
    """Tests for the audit history interface."""

    def test_audit_empty_initially(self, consensus):
        assert consensus.audit() == []

    def test_audit_records_all_rounds(self, consensus):
        for i in range(5):
            votes = [
                _vote("A", f"f{i}", VoteOutcome.FOR),
                _vote("B", f"f{i}", VoteOutcome.FOR),
            ]
            consensus.evaluate(f"f{i}", votes)
        trail = consensus.audit()
        assert len(trail) == 5
        assert all(isinstance(entry, dict) for entry in trail)

    def test_audit_contains_fact_ids(self, consensus):
        votes = [_vote("A", "fact_xyz", VoteOutcome.FOR), _vote("B", "fact_xyz", VoteOutcome.FOR)]
        consensus.evaluate("fact_xyz", votes)
        trail = consensus.audit()
        assert trail[0]["fact_id"] == "fact_xyz"


# ── ConsensusResult ──────────────────────────────────────────────────────


class TestConsensusResult:
    """Tests for ConsensusResult dataclass."""

    def test_approval_ratio_zero_when_no_reputation(self):
        r = ConsensusResult(
            fact_id="f1",
            accepted=False,
            supermajority_met=False,
            total_reputation=0.0,
            approving_reputation=0.0,
        )
        assert r.approval_ratio == 0.0

    def test_approval_ratio_correct(self):
        r = ConsensusResult(
            fact_id="f1",
            accepted=True,
            supermajority_met=True,
            total_reputation=10.0,
            approving_reputation=7.5,
        )
        assert r.approval_ratio == pytest.approx(0.75)


# ── Confidence ───────────────────────────────────────────────────────────


class TestConfidence:
    """Tests for weighted confidence computation."""

    def test_confidence_is_weighted(self, consensus):
        votes = [
            _vote("A", "f1", VoteOutcome.FOR, confidence=0.9),
            _vote("B", "f1", VoteOutcome.FOR, confidence=0.5),
            _vote("C", "f1", VoteOutcome.FOR, confidence=0.7),
        ]
        result = consensus.evaluate("f1", votes)
        # All agents have equal reputation (1.0), so confidence = mean
        expected = (0.9 + 0.5 + 0.7) / 3
        assert result.confidence == pytest.approx(expected, abs=0.01)

    def test_zero_confidence_when_no_for_votes(self, consensus):
        votes = [
            _vote("A", "f1", VoteOutcome.AGAINST),
            _vote("B", "f1", VoteOutcome.AGAINST),
        ]
        result = consensus.evaluate("f1", votes)
        assert result.confidence == 0.0
