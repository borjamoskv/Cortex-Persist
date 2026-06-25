# [C5-REAL] Exergy-Maximized
"""
Inefficiency Scanner. 
Identifies structural discrepancies in input graphs without simulation.
"""

import time
from typing import Protocol

from legacy_research.extensions.structural_arbitrage.models import ArbitrageSignal, CortexAmount


class MarketOracle(Protocol):
    """Protocol for fetching deterministic pricing data."""
    async def get_price(self, asset: str, venue: str) -> CortexAmount: ...


class InefficiencyScanner:
    """
    Scans physical market venues and constructs Epistemic Arbitrage Signals.
    """

    def __init__(self, oracle: MarketOracle) -> None:
        self.oracle = oracle

    async def scan_pair(self, asset_pair: str, venues: list[str]) -> list[ArbitrageSignal]:
        """
        Calculates asymmetric inefficiencies O(N^2) across venues.
        Returns structurally valid Arbitrage Signals.
        """
        signals = []
        prices = {}
        
        for venue in venues:
            prices[venue] = await self.oracle.get_price(asset_pair, venue)

        ts_ns = time.time_ns()

        for v_buy in venues:
            for v_sell in venues:
                if v_buy == v_sell:
                    continue
                
                buy_p = prices[v_buy]
                sell_p = prices[v_sell]
                
                if sell_p > buy_p:
                    signal = ArbitrageSignal.create(
                        asset_pair=asset_pair,
                        buy_venue=v_buy,
                        sell_venue=v_sell,
                        buy_price=buy_p,
                        sell_price=sell_p,
                        timestamp_ns=ts_ns
                    )
                    signals.append(signal)

        # Sort by maximum exergy margin descending
        signals.sort(key=lambda s: s.exergy_margin.raw_value, reverse=True)
        return signals
