"""
tests/test_gtm_specialist.py
─────────────────────────────
Tests for the GTM Pipeline Specialist (Vector T).

Covers:
  - Prospect phase lead generation & ICP filtering
  - Demo notebook URL generation
  - Close sequence stochastic discount bounds
  - EV gate rejection for low-value pipelines
  - Dry-run mode produces draft status (no side effects)
  - Full pipeline data flow (prospect → demo → close)
"""

from __future__ import annotations

import asyncio

import pytest

from cortex.swarm.gtm_specialist import GTMSpecialist, Lead, ICP_CRITERIA


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def specialist() -> GTMSpecialist:
    return GTMSpecialist()


def run_async(coro):
    """Helper to run async in sync test context."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ─── Test: Prospect generates leads ──────────────────────────────────────────


class TestProspectPhase:
    @pytest.mark.asyncio
    async def test_prospect_generates_leads(self, specialist):
        """Prospecting at scale=1 should return ICP-qualified leads."""
        leads = await specialist._prospect(scale=1)
        assert len(leads) > 0
        for lead in leads:
            assert isinstance(lead, Lead)
            assert lead.company
            assert lead.sector
            assert lead.pain_point

    @pytest.mark.asyncio
    async def test_prospect_scales_linearly(self, specialist):
        """Higher scale should produce more leads."""
        leads_1 = await specialist._prospect(scale=1)
        leads_2 = await specialist._prospect(scale=2)
        assert len(leads_2) >= len(leads_1)

    @pytest.mark.asyncio
    async def test_icp_filter_rejects_invalid_geo(self, specialist):
        """Leads outside ICP geos should be filtered out."""
        lead = Lead(
            company="Tokyo Corp",
            sector="Tech",
            pain_point="Support",
            geo="JP",
            proposed_tier_eur=1500,
        )
        assert not specialist._passes_icp(lead)

    @pytest.mark.asyncio
    async def test_icp_filter_rejects_under_budget(self, specialist):
        """Leads below minimum budget should be filtered out."""
        lead = Lead(
            company="Micro Corp",
            sector="Tech",
            pain_point="Support",
            geo="ES",
            proposed_tier_eur=100,  # Below 500 minimum
        )
        assert not specialist._passes_icp(lead)

    @pytest.mark.asyncio
    async def test_icp_filter_accepts_valid_lead(self, specialist):
        """Leads matching ICP should pass."""
        lead = Lead(
            company="Valid Corp",
            sector="Tech",
            pain_point="Automation",
            geo="ES",
            proposed_tier_eur=1500,
        )
        assert specialist._passes_icp(lead)


# ─── Test: Demo generation ───────────────────────────────────────────────────


class TestDemoPhase:
    @pytest.mark.asyncio
    async def test_demo_generation_produces_urls(self, specialist):
        """Demo phase should generate URLs for top leads."""
        leads = await specialist._prospect(scale=1)
        demo_leads = await specialist._prepare_demos(leads, dry_run=True)
        assert len(demo_leads) > 0
        for lead in demo_leads:
            assert lead.demo_url
            assert "demo.cortex-persist.dev" in lead.demo_url
            assert lead.pitch
            assert lead.status == "demo_draft"

    @pytest.mark.asyncio
    async def test_demo_conversion_rate(self, specialist):
        """Demo count should respect PROSPECT_TO_DEMO_RATE."""
        leads = await specialist._prospect(scale=1)
        demo_leads = await specialist._prepare_demos(leads, dry_run=True)
        expected_max = max(1, int(len(leads) * specialist.PROSPECT_TO_DEMO_RATE))
        assert len(demo_leads) <= expected_max

    def test_pitch_contains_company_name(self, specialist):
        """Pitch should be personalized with company name."""
        lead = Lead(
            company="TestCorp",
            sector="SaaS",
            pain_point="Churn",
            proposed_tier_eur=2000,
        )
        pitch = specialist._generate_pitch(lead)
        assert "TestCorp" in pitch
        assert "2000" in pitch or "2.000" in pitch

    def test_demo_url_dry_run_has_draft_marker(self, specialist):
        """Dry-run demo URLs should have DRAFT marker."""
        lead = Lead(company="TestCorp")
        url = specialist._generate_demo_url(lead, dry_run=True)
        assert "[DRAFT]" in url

    def test_demo_url_live_has_no_draft_marker(self, specialist):
        """Live demo URLs should NOT have DRAFT marker."""
        lead = Lead(company="TestCorp")
        url = specialist._generate_demo_url(lead, dry_run=False)
        assert "[DRAFT]" not in url


# ─── Test: Close sequence with stochastic discount ───────────────────────────


class TestClosePhase:
    def test_discount_bounds(self, specialist):
        """Stochastic discount must stay within [5%, 15%] range."""
        for _ in range(1000):
            discount = specialist._generate_discount()
            assert specialist.DISCOUNT_MIN_PCT <= discount <= specialist.DISCOUNT_MAX_PCT

    @pytest.mark.asyncio
    async def test_close_generates_stripe_links(self, specialist):
        """Close phase should generate Stripe payment links."""
        leads = await specialist._prospect(scale=1)
        demo_leads = await specialist._prepare_demos(leads, dry_run=True)
        close_leads = await specialist._generate_close_sequences(
            demo_leads, dry_run=True
        )
        assert len(close_leads) > 0
        for lead in close_leads:
            assert lead.stripe_link
            assert "stripe.com" in lead.stripe_link
            assert lead.discount_pct >= specialist.DISCOUNT_MIN_PCT
            assert lead.discount_pct <= specialist.DISCOUNT_MAX_PCT
            assert lead.status == "close_draft"

    @pytest.mark.asyncio
    async def test_close_conversion_rate(self, specialist):
        """Close count should respect DEMO_TO_CLOSE_RATE."""
        leads = await specialist._prospect(scale=1)
        demo_leads = await specialist._prepare_demos(leads, dry_run=True)
        close_leads = await specialist._generate_close_sequences(
            demo_leads, dry_run=True
        )
        expected_max = max(1, int(len(demo_leads) * specialist.DEMO_TO_CLOSE_RATE))
        assert len(close_leads) <= expected_max


# ─── Test: EV Gate ────────────────────────────────────────────────────────────


class TestEVGate:
    def test_ev_gate_rejects_low_value(self, specialist):
        """EV gate should reject when yield × confidence < cost × multiplier."""
        # cost=3.50 × multiplier=4.0 = 14.0 threshold
        assert not specialist.ev_gate(expected_yield=10.0, confidence=0.5)  # EV=5

    def test_ev_gate_accepts_high_value(self, specialist):
        """EV gate should accept when yield × confidence >= cost × multiplier."""
        assert specialist.ev_gate(expected_yield=100.0, confidence=0.5)  # EV=50 > 14


# ─── Test: Dry-run mode ──────────────────────────────────────────────────────


class TestDryRun:
    @pytest.mark.asyncio
    async def test_dry_run_no_side_effects(self, specialist):
        """Dry-run should produce draft status without any live actions."""
        result = await specialist.extract(dry_run=True, scale=1)
        assert result.status in ("dry_run", "skipped_ev")
        if result.status == "dry_run":
            assert result.gross_yield_usd > 0
            for opp in result.opportunities:
                assert opp["status"] in ("close_draft", "demo_draft", "prospect")

    @pytest.mark.asyncio
    async def test_dry_run_stripe_links_have_draft(self, specialist):
        """Dry-run Stripe links should contain DRAFT marker."""
        result = await specialist.extract(dry_run=True, scale=1)
        if result.status == "dry_run":
            for opp in result.opportunities:
                if opp.get("stripe_link"):
                    assert "[DRAFT]" in opp["stripe_link"]


# ─── Test: Full pipeline flow ────────────────────────────────────────────────


class TestPipelineFlow:
    @pytest.mark.asyncio
    async def test_pipeline_produces_valid_result(self, specialist):
        """Full extract() should return a valid ExtractionResult."""
        result = await specialist.extract(dry_run=True, scale=1)
        assert result.specialist_id == "gtm-cortex"
        assert result.vector == "T"
        assert result.duration_s > 0
        assert result.compute_cost_usd > 0
        assert isinstance(result.evidence, list)
        assert isinstance(result.opportunities, list)

    @pytest.mark.asyncio
    async def test_pipeline_evidence_has_three_phases(self, specialist):
        """Evidence should mention all 3 phases."""
        result = await specialist.extract(dry_run=True, scale=1)
        if result.status == "dry_run":
            evidence_text = " ".join(result.evidence)
            assert "Phase 1" in evidence_text
            assert "Phase 2" in evidence_text
            assert "Phase 3" in evidence_text

    @pytest.mark.asyncio
    async def test_pipeline_opportunities_have_lead_structure(self, specialist):
        """Each opportunity should have the Lead dict structure."""
        result = await specialist.extract(dry_run=True, scale=1)
        if result.status == "dry_run" and result.opportunities:
            opp = result.opportunities[0]
            assert "lead_id" in opp
            assert "company" in opp
            assert "sector" in opp
            assert "pain_point" in opp
            assert "proposed_tier_eur" in opp
            assert "confidence" in opp
            assert "discount_pct" in opp

    @pytest.mark.asyncio
    async def test_exergy_ratio_positive(self, specialist):
        """Net exergy should be positive for a viable pipeline."""
        result = await specialist.extract(dry_run=True, scale=1)
        if result.status == "dry_run":
            assert result.exergy_ratio > 1.0, (
                f"Exergy ratio {result.exergy_ratio} should be > 1.0"
            )
