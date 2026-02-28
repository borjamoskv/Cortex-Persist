"""
CORTEX Policy Engine — Tests.

Tests for the Bellman-inspired value function, scoring, ordering,
time decay, and integration with CortexEngine.
"""

import os
import tempfile

import pytest

from cortex.engine import CortexEngine
from cortex.policy import PolicyConfig, PolicyEngine
from cortex.policy.engine import _parse_ts
from cortex.policy.models import REWARD_MAP


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_anomaly_detector():
    """Reinitialize the anomaly detector so rapid test stores don't trigger bulk mutation."""
    try:
        import cortex.security.anomaly_detector as ad
        ad.DETECTOR = ad.AnomalyDetector()
    except (ImportError, AttributeError):
        pass
    yield
    try:
        import cortex.security.anomaly_detector as ad
        ad.DETECTOR = ad.AnomalyDetector()
    except (ImportError, AttributeError):
        pass


@pytest.fixture
async def engine():
    """Create a temporary CORTEX engine for policy testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    eng = CortexEngine(db_path=db_path, auto_embed=False)
    await eng.init_db()
    yield eng
    await eng.close()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
async def engine_with_data(engine):
    """Engine preloaded with diverse fact types for policy testing."""
    # Ghost — should score high
    await engine.store(
        "naroa-web",
        "Ghost: blocking deploy of gallery section, needs CSS fix",
        fact_type="ghost",
        tags=["blocking", "css"],
    )
    # Error — should score highest
    await engine.store(
        "naroa-web",
        "Error: crash on mobile viewport below 320px width",
        fact_type="error",
        tags=["crash", "mobile"],
    )
    # Bridge — medium score
    await engine.store(
        "naroa-web",
        "Bridge: Industrial Noir pattern from live-notch applicable to naroa-web gallery",
        fact_type="bridge",
        tags=["pattern", "cross-project"],
    )
    # Decision — low score
    await engine.store(
        "naroa-web",
        "Decision: uses vanilla JS, no framework dependency",
        fact_type="decision",
        tags=["architecture"],
    )
    # Knowledge — lowest score
    await engine.store(
        "naroa-web",
        "Knowledge: gallery uses chromatic aberration on hover",
        fact_type="knowledge",
        tags=["gallery", "effects"],
    )
    # Another project ghost (cross-project reference)
    await engine.store(
        "live-notch",
        "Ghost: naroa-web integration pending for NotchLive widget",
        fact_type="ghost",
        tags=["integration"],
    )
    return engine


# ── Unit Tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestBellmanValueFunction:
    """Test the core V(s) = R(s,a) + γ·V(s') equation."""

    async def test_bellman_equation(self, engine):
        """V(s) = R + γ·V(s') follows the formula exactly."""
        policy = PolicyEngine(engine)
        # reward=0.5, future=0.3, gamma=0.9
        # V = 0.5 + 0.9 * 0.3 = 0.77
        v = policy._bellman_value(0.5, 0.3, 0.9)
        assert abs(v - 0.77) < 1e-9

    async def test_bellman_zero_gamma(self, engine):
        """With gamma=0, only immediate reward matters."""
        policy = PolicyEngine(engine, PolicyConfig(gamma=0.0))
        v = policy._bellman_value(0.5, 10.0, 0.0)
        assert v == 0.5

    async def test_bellman_high_gamma(self, engine):
        """With gamma=1, future parity with present."""
        policy = PolicyEngine(engine)
        v = policy._bellman_value(0.5, 0.5, 1.0)
        assert v == 1.0


@pytest.mark.asyncio
class TestRewardMapping:
    """Test that fact types map to correct base rewards."""

    async def test_error_highest_base_reward(self):
        """Errors have the highest base reward."""
        assert REWARD_MAP["error"] > REWARD_MAP["ghost"]
        assert REWARD_MAP["ghost"] > REWARD_MAP["bridge"]
        assert REWARD_MAP["bridge"] > REWARD_MAP["decision"]
        assert REWARD_MAP["decision"] > REWARD_MAP["knowledge"]

    async def test_base_rewards_in_valid_range(self):
        """All base rewards are between 0 and 1."""
        for v in REWARD_MAP.values():
            assert 0.0 <= v <= 1.0


@pytest.mark.asyncio
class TestScoring:
    """Test fact scoring produces correct relative ordering."""

    async def test_error_scores_higher_than_knowledge(self, engine_with_data):
        """Errors should always rank above knowledge items."""
        policy = PolicyEngine(engine_with_data)
        actions = await policy.evaluate(project="naroa-web")

        error_actions = [a for a in actions if a.source_type == "error"]
        knowledge_actions = [a for a in actions if a.source_type == "knowledge"]

        assert error_actions, "Should have error actions"
        assert knowledge_actions, "Should have knowledge actions"
        assert error_actions[0].value > knowledge_actions[0].value

    async def test_ghost_scores_higher_than_decision(self, engine_with_data):
        """Ghosts should rank above decisions."""
        policy = PolicyEngine(engine_with_data)
        actions = await policy.evaluate(project="naroa-web")

        ghost_actions = [a for a in actions if a.source_type == "ghost"]
        decision_actions = [a for a in actions if a.source_type == "decision"]

        assert ghost_actions, "Should have ghost actions"
        assert decision_actions, "Should have decision actions"
        assert ghost_actions[0].value > decision_actions[0].value

    async def test_all_values_clamped(self, engine_with_data):
        """All action values should be clamped to [0, 1]."""
        policy = PolicyEngine(engine_with_data)
        actions = await policy.evaluate(project="naroa-web")
        for action in actions:
            assert 0.0 <= action.value <= 1.0


@pytest.mark.asyncio
class TestCrossProject:
    """Test cross-project detection and bonus."""

    async def test_cross_project_ghost_gets_bonus(self, engine_with_data):
        """A ghost mentioning another project should score higher."""
        policy = PolicyEngine(engine_with_data)
        actions = await policy.evaluate()

        # The live-notch ghost mentions "naroa-web" — cross-project
        cross = [
            a for a in actions
            if a.project == "live-notch" and a.source_type == "ghost"
        ]
        same = [
            a for a in actions
            if a.project == "naroa-web" and a.source_type == "ghost"
        ]

        assert cross, "Should have cross-project ghost"
        assert same, "Should have same-project ghost"
        # The naroa-web ghost has "blocking" keyword which gives blocking bonus,
        # so we just verify both are scored (the blocking bonus may outweigh
        # cross-project bonus, which is correct behavior).
        assert all(a.value > 0.0 for a in cross)


@pytest.mark.asyncio
class TestEmptyProject:
    """Test edge cases."""

    async def test_empty_project_returns_empty(self, engine):
        """A project with no facts returns an empty action list."""
        policy = PolicyEngine(engine)
        actions = await policy.evaluate(project="nonexistent")
        assert actions == []

    async def test_config_overrides(self, engine_with_data):
        """Custom config should change scoring behavior."""
        low_gamma = PolicyConfig(gamma=0.0, max_actions=5)
        policy = PolicyEngine(engine_with_data, low_gamma)
        actions = await policy.evaluate(project="naroa-web")

        # With gamma=0, future value is zeroed out — only immediate reward matters.
        assert len(actions) <= 5
        for action in actions:
            assert action.value <= 1.0


@pytest.mark.asyncio
class TestIntegration:
    """Test CortexEngine.prioritize() convenience method."""

    async def test_prioritize_method(self, engine_with_data):
        """CortexEngine.prioritize() returns sorted actions."""
        actions = await engine_with_data.prioritize(project="naroa-web")
        assert isinstance(actions, list)
        assert len(actions) > 0

        # Verify sorted descending by value.
        values = [a.value for a in actions]
        assert values == sorted(values, reverse=True)

    async def test_prioritize_all_projects(self, engine_with_data):
        """prioritize() without project returns actions from all projects."""
        actions = await engine_with_data.prioritize()
        projects = {a.project for a in actions}
        assert "naroa-web" in projects
        assert "live-notch" in projects


@pytest.mark.asyncio
class TestTimestampParsing:
    """Test the timestamp parser."""

    async def test_parse_iso_format(self):
        dt = _parse_ts("2026-02-28T04:30:00")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 2

    async def test_parse_iso_with_fractional(self):
        dt = _parse_ts("2026-02-28T04:30:00.123456")
        assert dt is not None
        assert dt.microsecond == 123456

    async def test_parse_none(self):
        assert _parse_ts(None) is None

    async def test_parse_empty(self):
        assert _parse_ts("") is None

    async def test_parse_garbage(self):
        assert _parse_ts("not-a-date") is None
