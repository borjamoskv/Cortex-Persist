"""Unit tests for Vector L — PYME Bottleneck Detection Engine.

Tests:
    - BottleneckScorer: signal aggregation and tier assignment
    - PitchComposer: template fallback composition
    - VectorLLedger: lifecycle state transitions
    - VectorLAgent: tick cycle with mocked probes
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cortex.agents.builtins.vector_l_ledger import ProspectStage, VectorLLedger
from cortex.agents.builtins.vector_l_probe import (
    ProspectSignal,
    score_company,
    tier_from_score,
)

# ── score_company ─────────────────────────────────────────────────────────────


class TestBottleneckScorer:
    def _sig(self, source: str, score: float, company: str = "Acme") -> ProspectSignal:
        return ProspectSignal(
            company=company,
            domain=None,
            source=source,
            raw_score=score,
            evidence=f"test signal from {source}",
        )

    def test_empty_signals_returns_zero(self):
        assert score_company([]) == 0.0

    def test_single_signal_scores_correctly(self):
        sig = self._sig("linkedin", 0.8)
        gap = score_company([sig], employee_count=50)
        assert 0.0 < gap <= 1.0

    def test_high_signals_produce_high_gap(self):
        signals = [
            self._sig("linkedin", 1.0),
            self._sig("glassdoor", 1.0),
            self._sig("indeed", 1.0),
        ]
        gap = score_company(signals, employee_count=100)
        assert gap > 0.70

    def test_low_signals_produce_low_gap(self):
        signals = [self._sig("linkedin", 0.1), self._sig("indeed", 0.05)]
        gap = score_company(signals, employee_count=20)
        assert gap < 0.55

    def test_size_factor_amplifies_score(self):
        sigs = [self._sig("linkedin", 0.7)]
        small = score_company(sigs, employee_count=10)
        large = score_company(sigs, employee_count=500)
        assert large > small

    def test_score_capped_at_one(self):
        signals = [self._sig(s, 1.0) for s in ["linkedin", "glassdoor", "github_org", "indeed"]]
        assert score_company(signals, employee_count=9999) <= 1.0


# ── tier_from_score ───────────────────────────────────────────────────────────


class TestTierFromScore:
    @pytest.mark.parametrize(
        "gap, expected_tier",
        [
            (0.40, 0),
            (0.55, 500),
            (0.65, 500),
            (0.70, 1000),
            (0.80, 1000),
            (0.85, 2000),
            (0.99, 2000),
        ],
    )
    def test_tier_boundaries(self, gap: float, expected_tier: int):
        assert tier_from_score(gap) == expected_tier


# ── VectorLLedger ─────────────────────────────────────────────────────────────


class TestVectorLLedger:
    @pytest.fixture
    def ledger(self):
        return VectorLLedger(engine=None)  # in-memory

    @pytest.mark.asyncio
    async def test_discover_returns_prospect_id(self, ledger):
        pid = await ledger.discover(
            company="TestCorp",
            sources=["linkedin"],
            signals_summary="3 ops roles open",
        )
        assert "testcorp" in pid.lower()
        assert pid.startswith("vl_")

    @pytest.mark.asyncio
    async def test_discover_stores_in_memory(self, ledger):
        await ledger.discover(company="Widget Inc", sources=["indeed"], signals_summary="data entry")
        assert len(ledger._store) == 1

    @pytest.mark.asyncio
    async def test_score_writes_fact(self, ledger):
        pid = await ledger.discover("XyzCorp", ["glassdoor"], "manual processes")
        await ledger.score(pid, "XyzCorp", exergy_gap=0.75, tier=1000)
        assert len(ledger._store) >= 2

    @pytest.mark.asyncio
    async def test_convert_increases_mrr(self, ledger):
        assert ledger.mrr_total() == 0
        await ledger.convert(
            prospect_id="vl_test123",
            company="PayingCustomer",
            tier=2000,
            subscription_id="sub_abc",
        )
        assert ledger.mrr_total() == 2000

    @pytest.mark.asyncio
    async def test_multiple_conversions_sum_mrr(self, ledger):
        await ledger.convert("vl_a", "Company A", tier=500)
        await ledger.convert("vl_b", "Company B", tier=1000)
        assert ledger.mrr_total() == 1500

    @pytest.mark.asyncio
    async def test_list_prospects_all(self, ledger):
        await ledger.discover("Alpha", ["linkedin"], "evidence")
        await ledger.discover("Beta", ["indeed"], "evidence")
        prospects = ledger.list_prospects()
        assert len(prospects) == 2

    @pytest.mark.asyncio
    async def test_list_prospects_filter_by_stage(self, ledger):
        await ledger.convert("vl_x", "Converted Co", tier=500)
        await ledger.discover("Pending Co", ["linkedin"], "evidence")
        converted = ledger.list_prospects(stage=ProspectStage.CONVERTED)
        assert len(converted) == 1
        assert converted[0]["metadata"]["company"] == "Converted Co"

    @pytest.mark.asyncio
    async def test_hours_saved_500_tier(self):
        assert VectorLLedger._estimate_hours_saved(500) == 8.0

    @pytest.mark.asyncio
    async def test_hours_saved_2000_tier(self):
        assert VectorLLedger._estimate_hours_saved(2000) == 40.0


# ── PitchComposer (template fallback) ─────────────────────────────────────────


class TestPitchComposer:
    @pytest.mark.asyncio
    async def test_template_fallback_when_no_api_key(self):
        from cortex.agents.builtins.vector_l_pitcher import PitchComposer

        composer = PitchComposer()
        # Ensure no API key → template path
        composer._api_key = ""

        result = await composer.compose(
            company="TestCorp",
            signals_summary="3 data entry roles open",
            tier=500,
            sources=["linkedin"],
            sender_name="Borja",
        )
        assert "subject" in result
        assert "body" in result
        assert result["variant"] == "template"
        assert "TestCorp" in result["body"] or "TestCorp" in result["subject"]

    @pytest.mark.asyncio
    async def test_compose_includes_tier_price(self):
        from cortex.agents.builtins.vector_l_pitcher import PitchComposer

        composer = PitchComposer()
        composer._api_key = ""
        result = await composer.compose(
            company="Demo Inc",
            signals_summary="manual processes",
            tier=1000,
            sources=["glassdoor"],
        )
        body_or_subject = result["body"] + result["subject"]
        assert "1000" in body_or_subject or "$1,000" in body_or_subject or "1,000" in body_or_subject


# ── VectorLAgent — tick cycle ─────────────────────────────────────────────────


class TestVectorLAgent:
    def _make_agent(self, dry_run: bool = True) -> VectorLAgent:
        from cortex.agents.builtins.vector_l_agent import VectorLAgent

        bus = MagicMock()
        bus.receive = AsyncMock(return_value=None)
        bus.send = AsyncMock()
        agent = VectorLAgent(bus=bus, engine=None, dry_run=dry_run, scan_query="test query")
        # Force scan interval to 0 so tick runs immediately
        agent._scan_interval = 0
        agent._min_exergy_gap = 0.0  # ensure everything is pitchable
        return agent

    def _fake_signals(self) -> list[ProspectSignal]:
        return [
            ProspectSignal(
                company="Acme PYME",
                domain="acme.com",
                source="linkedin",
                raw_score=0.9,
                evidence="5 ops roles: data entry, admin, coordinator",
            ),
            ProspectSignal(
                company="Widget SL",
                domain=None,
                source="indeed",
                raw_score=0.7,
                evidence="3 back-office roles",
            ),
        ]

    @pytest.mark.asyncio
    async def test_tick_runs_and_writes_ledger(self):
        agent = self._make_agent(dry_run=True)
        fake_signals = self._fake_signals()

        with patch.object(agent, "_run_probes", new=AsyncMock(return_value=fake_signals)):
            await agent.tick()

        # Ledger should have had items written
        assert len(agent.ledger._store) > 0

    @pytest.mark.asyncio
    async def test_tick_increments_pitch_counter(self):
        agent = self._make_agent(dry_run=True)
        fake_signals = self._fake_signals()

        with patch.object(agent, "_run_probes", new=AsyncMock(return_value=fake_signals)):
            with patch.object(agent._email, "send", new=AsyncMock(return_value=True)):
                await agent.tick()

        assert agent._pitches_this_cycle > 0
        assert agent._total_pitches == agent._pitches_this_cycle

    @pytest.mark.asyncio
    async def test_tick_respects_cooldown(self):
        agent = self._make_agent(dry_run=True)
        agent._scan_interval = 9999  # far future
        agent._last_scan_ts = time.time()

        called = []

        async def mock_run_probes():
            called.append(True)
            return []

        with patch.object(agent, "_run_probes", new=mock_run_probes):
            # tick should sleep (cooldown), not scan
            try:
                await asyncio.wait_for(agent.tick(), timeout=0.5)
            except asyncio.TimeoutError:
                pass  # expected — sleeping in cooldown

        assert not called, "Probes should not run during cooldown"

    @pytest.mark.asyncio
    async def test_stats_returns_expected_keys(self):
        agent = self._make_agent()
        stats = agent.stats
        assert "phase" in stats
        assert "total_pitches" in stats
        assert "mrr_usd" in stats
