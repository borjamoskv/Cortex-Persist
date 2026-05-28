"""Tests for the Cognitive Fingerprint Extractor."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cortex.extensions.fingerprint.extractor import FingerprintExtractor
from cortex.extensions.fingerprint.models import CognitiveFingerprint


def _make_engine() -> MagicMock:
    """Build a mock CortexEngine with a functional session() context manager."""
    engine = MagicMock()
    engine.session = AsyncMock()
    return engine


def _patch_scanner(mock_data: dict):
    """Patch FingerprintScanner with controlled return values."""
    scanner_patch = patch(
        "cortex.extensions.fingerprint.extractor.FingerprintScanner", autospec=True
    )
    return scanner_patch, mock_data


async def _run(engine, project=None):
    return await FingerprintExtractor.extract(engine, project)


# ─── Helpers ──────────────────────────────────────────────────────────────


def _mock_scanner(
    total: int = 50,
    type_dist: dict | None = None,
    conf_dist: dict | None = None,
    n_projects: int = 5,
    avg_len: float = 300.0,
    recent: int = 20,
    total_count: int = 50,
    active_days: int = 30,
    span_days: float = 60.0,
    domain_profiles: list | None = None,
    weekly_velocity: dict | None = None,
):
    m = AsyncMock()
    m.total_facts.return_value = total
    m.fact_type_distribution.return_value = type_dist or {
        "decision": 25,
        "error": 5,
        "bridge": 10,
        "discovery": 5,
        "ghost": 5,
    }
    m.confidence_distribution.return_value = conf_dist or {
        "C5": 20,
        "C4": 10,
        "C3": 10,
        "C2": 5,
        "C1": 5,
    }
    m.distinct_projects.return_value = n_projects
    m.avg_content_length.return_value = avg_len
    m.recency_ratio.return_value = (recent, total_count)
    m.active_days.return_value = (active_days, span_days)
    m.domain_profiles.return_value = domain_profiles or [
        {
            "project": "CORTEX",
            "fact_type": "decision",
            "count": 25,
            "avg_len": 350.0,
            "recency_days": 2.0,
            "dominant_source": "agent:gemini",
            "avg_confidence_weight": 0.9,
        }
    ]
    m.weekly_velocity_per_domain.return_value = weekly_velocity or {
        ("CORTEX", "decision"): 3.5,
    }
    return m


# ─── Tests ────────────────────────────────────────────────────────────────


class TestFingerprintEmpty:
    @pytest.mark.asyncio
    async def test_empty_db_returns_null_state(self):
        engine = _make_engine()
        with patch("cortex.extensions.fingerprint.extractor.FingerprintScanner") as MockScanner:
            m = AsyncMock()
            m.total_facts.return_value = 0
            MockScanner.return_value = m
            fp = await _run(engine)

        assert isinstance(fp, CognitiveFingerprint)
        assert fp.archetype == "null_state"
        assert fp.total_facts_analyzed == 0
        assert fp.fingerprint_completeness == 0.0


class TestPatternVector:
    @pytest.mark.asyncio
    async def test_risk_tolerance_computed_correctly(self):
        """C3+C4+C5 = 40 of 50 → risk_tolerance = 0.8."""
        engine = _make_engine()
        with patch("cortex.extensions.fingerprint.extractor.FingerprintScanner") as MockScanner:
            MockScanner.return_value = _mock_scanner(
                total=50,
                conf_dist={"C5": 20, "C4": 10, "C3": 10, "C2": 5, "C1": 5},
            )
            fp = await _run(engine)

        assert fp.pattern.risk_tolerance == pytest.approx(0.8, abs=0.01)

    @pytest.mark.asyncio
    async def test_synthesis_drive_from_bridges(self):
        """bridge=10 + discovery=5 of 50 total → synthesis_drive = 0.30."""
        engine = _make_engine()
        with patch("cortex.extensions.fingerprint.extractor.FingerprintScanner") as MockScanner:
            MockScanner.return_value = _mock_scanner(
                total=50,
                type_dist={"decision": 35, "bridge": 10, "discovery": 5},
            )
            fp = await _run(engine)

        assert fp.pattern.synthesis_drive == pytest.approx(0.30, abs=0.01)

    @pytest.mark.asyncio
    async def test_session_density_capped_at_one(self):
        """20 facts/day over 10 days → density = 20/10 = 2.0 facts/day.
        Normalized: 2.0/10.0 = 0.20 (cap is 10 facts/day)."""
        engine = _make_engine()
        with patch("cortex.extensions.fingerprint.extractor.FingerprintScanner") as MockScanner:
            MockScanner.return_value = _mock_scanner(total=20, active_days=10)
            fp = await _run(engine)

        assert 0.0 <= fp.pattern.session_density <= 1.0

    @pytest.mark.asyncio
    async def test_recency_bias_calculation(self):
        """40 of 50 facts in last 30 days → recency_bias = 0.8."""
        engine = _make_engine()
        with patch("cortex.extensions.fingerprint.extractor.FingerprintScanner") as MockScanner:
            MockScanner.return_value = _mock_scanner(total=50, recent=40, total_count=50)
            fp = await _run(engine)

        assert fp.pattern.recency_bias == pytest.approx(0.8, abs=0.01)


class TestArchetype:
    @pytest.mark.asyncio
    async def test_archetype_field_populated(self):
        engine = _make_engine()
        with patch("cortex.extensions.fingerprint.extractor.FingerprintScanner") as MockScanner:
            MockScanner.return_value = _mock_scanner()
            fp = await _run(engine)

        assert fp.archetype != "unknown"
        assert fp.archetype_confidence >= 0.0
        assert fp.archetype_confidence <= 1.0

    @pytest.mark.asyncio
    async def test_bold_experimenter_high_risk(self):
        """Pure C5 facts, no errors → should lean bold_experimenter or sovereign."""
        engine = _make_engine()
        with patch("cortex.extensions.fingerprint.extractor.FingerprintScanner") as MockScanner:
            MockScanner.return_value = _mock_scanner(
                total=100,
                conf_dist={"C5": 100},
                type_dist={"decision": 100},
                n_projects=20,
            )
            fp = await _run(engine)

        # high risk_tolerance = not cautious_guardian
        assert fp.archetype != "cautious_guardian"


class TestDomainPreferences:
    @pytest.mark.asyncio
    async def test_domain_preferences_populated(self):
        engine = _make_engine()
        with patch("cortex.extensions.fingerprint.extractor.FingerprintScanner") as MockScanner:
            MockScanner.return_value = _mock_scanner()
            fp = await _run(engine)

        assert len(fp.domain_preferences) == 1
        dp = fp.domain_preferences[0]
        assert dp.project == "CORTEX"
        assert dp.fact_type == "decision"
        assert dp.store_frequency_per_week == pytest.approx(3.5, abs=0.01)

    @pytest.mark.asyncio
    async def test_domain_confidence_weight_passed_through(self):
        engine = _make_engine()
        with patch("cortex.extensions.fingerprint.extractor.FingerprintScanner") as MockScanner:
            MockScanner.return_value = _mock_scanner()
            fp = await _run(engine)

        assert fp.domain_preferences[0].avg_confidence_weight == pytest.approx(0.9, abs=0.01)


class TestSerialization:
    @pytest.mark.asyncio
    async def test_to_dict_keys_present(self):
        engine = _make_engine()
        with patch("cortex.extensions.fingerprint.extractor.FingerprintScanner") as MockScanner:
            MockScanner.return_value = _mock_scanner()
            fp = await _run(engine)

        d = fp.to_dict()
        assert "archetype" in d
        assert "pattern" in d
        assert "domain_preferences" in d
        for key in (
            "risk_tolerance",
            "caution_index",
            "synthesis_drive",
            "session_density",
            "recency_bias",
            "breadth",
            "depth_preference",
        ):
            assert key in d["pattern"]

    @pytest.mark.asyncio
    async def test_to_agent_prompt_contains_archetype(self):
        engine = _make_engine()
        with patch("cortex.extensions.fingerprint.extractor.FingerprintScanner") as MockScanner:
            MockScanner.return_value = _mock_scanner()
            fp = await _run(engine)

        prompt = fp.to_agent_prompt()
        assert "Cognitive Fingerprint" in prompt
        assert "Risk Tolerance" in prompt
        assert "Caution Index" in prompt

    @pytest.mark.asyncio
    async def test_completeness_grows_with_data(self):
        """More facts → higher completeness."""
        engine = _make_engine()
        with patch("cortex.extensions.fingerprint.extractor.FingerprintScanner") as MockScanner:
            MockScanner.return_value = _mock_scanner(total=10)
            fp_small = await _run(engine)

        with patch("cortex.extensions.fingerprint.extractor.FingerprintScanner") as MockScanner:
            MockScanner.return_value = _mock_scanner(total=100)
            fp_large = await _run(engine)

        assert fp_large.fingerprint_completeness >= fp_small.fingerprint_completeness
