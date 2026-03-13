"""Unit tests for cortex.wealth.scanner — FundingRateScanner.

Deterministic via seed injection. No network IO.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from cortex.wealth.scanner import FundingRateScanner

SEED = 42


@pytest.fixture
def scanner() -> FundingRateScanner:
    return FundingRateScanner(random_seed=SEED)


# ── Determinism ──────────────────────────────────────────────────────


class TestDeterminism:
    async def test_same_seed_same_results(self):
        s1 = FundingRateScanner(random_seed=SEED)
        s2 = FundingRateScanner(random_seed=SEED)
        r1 = await s1.scan_opportunities(["BTC", "ETH"])
        r2 = await s2.scan_opportunities(["BTC", "ETH"])
        assert len(r1) == len(r2)
        for a, b in zip(r1, r2, strict=True):
            assert a.asset == b.asset
            assert a.net_rate_8h == b.net_rate_8h


# ── Sorting ──────────────────────────────────────────────────────────


class TestSorting:
    async def test_sorted_by_apr_descending(self, scanner):
        results = await scanner.scan_opportunities(["BTC", "ETH", "SOL", "ARB", "OP"])
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i].estimated_apr >= results[i + 1].estimated_apr


# ── Viability filter ─────────────────────────────────────────────────


class TestViability:
    async def test_all_results_are_viable(self, scanner):
        results = await scanner.scan_opportunities(["BTC", "ETH", "SOL"])
        for opp in results:
            assert opp.is_viable


# ── Risk assessment ──────────────────────────────────────────────────


class TestRiskAssessment:
    def test_both_onchain_is_high(self):
        assert FundingRateScanner.assess_risk("hyperliquid", "dydx") == "high"

    def test_mixed_is_medium(self):
        assert FundingRateScanner.assess_risk("binance", "gmx") == "medium"

    def test_both_cex_is_low(self):
        assert FundingRateScanner.assess_risk("binance", "bybit") == "low"


# ── FundingArbitrage ─────────────────────────────────────────────────


class TestFundingArbitrage:
    def test_not_viable_low_liquidity(self):
        from cortex.wealth.scanner import FundingArbitrage

        opp = FundingArbitrage(
            asset="TEST",
            exchange_long="binance",
            exchange_short="bybit",
            funding_rate_long=Decimal("-0.0003"),
            funding_rate_short=Decimal("0.0003"),
            net_rate_8h=Decimal("0.0006"),
            estimated_apr=Decimal("0.657"),
            size_liquidity=Decimal("50000"),  # Below 100k threshold
            execution_risk="low",
        )
        assert opp.is_viable is False

    def test_not_viable_low_spread(self):
        from cortex.wealth.scanner import FundingArbitrage

        opp = FundingArbitrage(
            asset="TEST",
            exchange_long="binance",
            exchange_short="bybit",
            funding_rate_long=Decimal("-0.00005"),
            funding_rate_short=Decimal("0.00005"),
            net_rate_8h=Decimal("0.0001"),  # Below 0.02% threshold
            estimated_apr=Decimal("0.1095"),
            size_liquidity=Decimal("500000"),
            execution_risk="low",
        )
        assert opp.is_viable is False
