"""Tests for the Haiku Poet-Compactor (3-agent swarm)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cortex.compaction.strategies.haiku_compress import (
    HaikuSwarm,
    _ScoredCandidate,
)

# ─── Fixtures ────────────────────────────────────────────────────────

SAMPLE_CONTENT = (
    "The CORTEX memory system uses SHA-256 hashing to ensure "
    "ledger integrity. Each fact is cryptographically chained "
    "to its predecessor, creating an immutable audit trail."
)

SAMPLE_HAIKU = (
    "Chains of hashed truths grow\n"
    "Each fact locked to what came first\n"
    "Memory stays pure"
)

SAMPLE_HAIKU_2 = (
    "Ledger chains persist\n"
    "Cryptographic bonds hold fast\n"
    "No truth can be lost"
)

SAMPLE_HAIKU_3 = (
    "Facts etched deep in hash\n"
    "Immutable audit trail\n"
    "Trust carved into code"
)

CRITIC_RESPONSE = (
    '[{"haiku": "Chains of hashed truths grow\\nEach fact locked to what came first\\n'
    'Memory stays pure", "fidelity": 0.92},'
    '{"haiku": "Ledger chains persist\\nCryptographic bonds hold fast\\n'
    'No truth can be lost", "fidelity": 0.85},'
    '{"haiku": "Facts etched deep in hash\\nImmutable audit trail\\n'
    'Trust carved into code", "fidelity": 0.78}]'
)


@pytest.fixture
def swarm():
    """HaikuSwarm with mocked client."""
    s = HaikuSwarm()
    s._client = MagicMock()  # Prevent real client init
    return s


# ─── Unit Tests ──────────────────────────────────────────────────────


class TestHaikuSwarmAgents:
    """Test individual swarm agents."""

    def test_poet_generates_candidates(self, swarm: HaikuSwarm):
        """Poet agent should return multiple haiku candidates."""
        mock_response = f"{SAMPLE_HAIKU}\n\n{SAMPLE_HAIKU_2}\n\n{SAMPLE_HAIKU_3}"

        with patch.object(swarm, "_call_llm", return_value=mock_response):
            candidates = swarm._poet_agent(SAMPLE_CONTENT, "knowledge")

        assert len(candidates) >= 2
        for c in candidates:
            lines = c.strip().split("\n")
            assert len(lines) == 3

    def test_critic_scores_fidelity(self, swarm: HaikuSwarm):
        """Critic agent should return scored candidates."""
        candidates = [SAMPLE_HAIKU, SAMPLE_HAIKU_2, SAMPLE_HAIKU_3]

        with patch.object(swarm, "_call_llm", return_value=CRITIC_RESPONSE):
            scored = swarm._critic_agent(SAMPLE_CONTENT, candidates)

        assert len(scored) == 3
        assert all(isinstance(s, _ScoredCandidate) for s in scored)
        assert all(0.0 <= s.fidelity <= 1.0 for s in scored)
        # Highest score should be first candidate
        assert scored[0].fidelity == 0.92

    def test_critic_fallback_on_bad_json(self, swarm: HaikuSwarm):
        """Critic should assign uniform scores when JSON parsing fails."""
        candidates = [SAMPLE_HAIKU, SAMPLE_HAIKU_2]

        with patch.object(swarm, "_call_llm", return_value="not valid json"):
            scored = swarm._critic_agent(SAMPLE_CONTENT, candidates)

        assert len(scored) == 2
        assert all(s.fidelity == 0.5 for s in scored)

    def test_judge_selects_valid(self, swarm: HaikuSwarm):
        """Judge should select highest-fidelity structurally valid candidate."""
        scored = [
            _ScoredCandidate(haiku=SAMPLE_HAIKU, fidelity=0.92),
            _ScoredCandidate(haiku=SAMPLE_HAIKU_2, fidelity=0.85),
        ]

        selected = swarm._judge_agent(scored)
        # Should select the highest-fidelity one (0.92)
        assert selected is not None
        assert "Chains of hashed truths" in selected or selected == SAMPLE_HAIKU


class TestHaikuSwarmPipeline:
    """Test the full Poet → Critic → Judge pipeline."""

    def test_compose_full_pipeline(self, swarm: HaikuSwarm):
        """Full pipeline should produce a valid HaikuResult."""
        call_count = 0

        def mock_llm(system, user, temperature=0.5):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # Poet
                return f"{SAMPLE_HAIKU}\n\n{SAMPLE_HAIKU_2}\n\n{SAMPLE_HAIKU_3}"
            elif call_count == 2:  # Critic
                return CRITIC_RESPONSE
            else:  # Judge (if needed)
                return SAMPLE_HAIKU

        with patch.object(swarm, "_call_llm", side_effect=mock_llm):
            result = swarm.compose(SAMPLE_CONTENT, "knowledge")

        assert result.was_composed
        assert result.haiku
        assert result.candidates_generated >= 2
        assert result.fidelity_score > 0.0

    def test_compose_empty_poet(self, swarm: HaikuSwarm):
        """Pipeline should gracefully handle empty poet output."""
        with patch.object(swarm, "_call_llm", return_value=""):
            result = swarm.compose(SAMPLE_CONTENT, "knowledge")

        assert not result.was_composed
        assert result.error


class TestCompressFact:
    """Test single fact compression."""

    def test_skips_existing_haiku(self, swarm: HaikuSwarm):
        """Facts with _haiku in meta should be skipped."""
        result = swarm.compress_fact(
            fact_id=42,
            content=SAMPLE_CONTENT,
            meta={"_haiku": SAMPLE_HAIKU},
        )
        assert not result.was_composed
        assert result.haiku == SAMPLE_HAIKU

    def test_skips_short_content(self, swarm: HaikuSwarm):
        """Facts shorter than 30 chars should be skipped."""
        result = swarm.compress_fact(
            fact_id=42,
            content="Too short",
            meta={},
        )
        assert not result.was_composed
        assert "too short" in (result.error or "").lower()

    def test_dry_run_no_llm(self, swarm: HaikuSwarm):
        """Dry run should skip LLM calls entirely."""
        result = swarm.compress_fact(
            fact_id=42,
            content=SAMPLE_CONTENT,
            meta={},
            dry_run=True,
        )
        assert result.was_composed
        assert "DRY RUN" in result.haiku


class TestStrategyEnum:
    """Test compactor integration."""

    def test_haiku_compress_in_enum(self):
        """HAIKU_COMPRESS should be in CompactionStrategy."""
        from cortex.compaction.compactor import CompactionStrategy

        assert hasattr(CompactionStrategy, "HAIKU_COMPRESS")
        assert CompactionStrategy.HAIKU_COMPRESS.value == "haiku_compress"
        assert CompactionStrategy.HAIKU_COMPRESS in CompactionStrategy.all()


class TestCriticParsing:
    """Test critic response parsing edge cases."""

    def test_parse_with_markdown_fences(self):
        """Critic response with markdown code fences should parse correctly."""
        raw = f"```json\n{CRITIC_RESPONSE}\n```"
        candidates = [SAMPLE_HAIKU, SAMPLE_HAIKU_2, SAMPLE_HAIKU_3]
        scored = HaikuSwarm._parse_critic_response(raw, candidates)
        assert len(scored) == 3
        assert scored[0].fidelity == 0.92

    def test_parse_empty_response(self):
        """Empty response should return fallback scores."""
        scored = HaikuSwarm._parse_critic_response(
            "", [SAMPLE_HAIKU, SAMPLE_HAIKU_2]
        )
        assert len(scored) == 2
        assert all(s.fidelity == 0.5 for s in scored)

    def test_decode_meta_json_string(self):
        """JSON string metadata should decode correctly."""
        meta = HaikuSwarm._decode_meta('{"_haiku": "test"}')
        assert meta == {"_haiku": "test"}

    def test_decode_meta_dict(self):
        """Dict metadata should pass through."""
        meta = HaikuSwarm._decode_meta({"key": "val"})
        assert meta == {"key": "val"}

    def test_decode_meta_none(self):
        """None metadata should return empty dict."""
        meta = HaikuSwarm._decode_meta(None)
        assert meta == {}
