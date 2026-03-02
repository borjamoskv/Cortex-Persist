"""CORTEX Revenue — Vector 2: Arbitrage Scanner.

Detects price discrepancies across public marketplaces and digital goods
platforms. Detection only by default — execution requires explicit opt-in.

Pipeline:
    1. Data Collection → query pricing APIs / scrape public listings
    2. Discrepancy Detection → cross-reference prices across platforms
    3. Opportunity Scoring → calculate margin after fees
    4. Alert → notify via CORTEX + macOS notification
    5. Optional Execution → manual by default

Supported domains:
    - Expired domains with SEO value
    - Digital goods (templates, assets, fonts, licenses)
    - Freelance rate arbitrage (geographic pricing differences)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from cortex.revenue.models import (
    ExecutionResult,
    Opportunity,
    VectorType,
)

logger = logging.getLogger("cortex.revenue.arbitrage")


@dataclass
class PricePoint:
    """A price observation from a specific source.

    Attributes:
        item_id: Unique item identifier across sources.
        source: Platform or marketplace name.
        price: Price in EUR.
        url: Direct link to the listing.
        meta: Source-specific metadata.
    """

    item_id: str
    source: str
    price: Decimal
    url: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class ArbitrageOpportunity:
    """A detected price discrepancy between two sources.

    Attributes:
        item_id: The item being compared.
        buy: The lower price point (buy side).
        sell: The higher price point (sell side).
        margin_pct: Percentage margin after fees.
        fees_estimate: Estimated transaction fees.
    """

    item_id: str
    buy: PricePoint
    sell: PricePoint
    fees_estimate: Decimal = Decimal("0")

    @property
    def gross_margin(self) -> Decimal:
        """Gross margin = sell - buy."""
        return self.sell.price - self.buy.price

    @property
    def net_margin(self) -> Decimal:
        """Net margin = gross - fees."""
        return self.gross_margin - self.fees_estimate

    @property
    def margin_pct(self) -> float:
        """Margin as percentage of buy price."""
        if self.buy.price == 0:
            return 0.0
        return float(self.net_margin / self.buy.price * 100)


# ─── Mock Data Sources (Replace with real APIs) ───────────────

MOCK_DOMAIN_LISTINGS: list[dict[str, Any]] = [
    {
        "item_id": "aitools.dev",
        "sources": [
            {"source": "GoDaddy Auctions", "price": Decimal("45"), "url": "https://auctions.godaddy.com"},
            {"source": "Afternic", "price": Decimal("299"), "url": "https://afternic.com"},
        ],
    },
    {
        "item_id": "datastudio.io",
        "sources": [
            {"source": "Namecheap", "price": Decimal("12"), "url": "https://namecheap.com"},
            {"source": "Sedo", "price": Decimal("180"), "url": "https://sedo.com"},
        ],
    },
    {
        "item_id": "promptengineering.app",
        "sources": [
            {"source": "Dynadot", "price": Decimal("25"), "url": "https://dynadot.com"},
            {"source": "Dan.com", "price": Decimal("450"), "url": "https://dan.com"},
        ],
    },
]

MOCK_DIGITAL_GOODS: list[dict[str, Any]] = [
    {
        "item_id": "minimal-dashboard-template",
        "sources": [
            {"source": "Gumroad", "price": Decimal("15"), "url": "https://gumroad.com"},
            {"source": "ThemeForest", "price": Decimal("49"), "url": "https://themeforest.net"},
        ],
    },
    {
        "item_id": "icon-pack-3d-glass",
        "sources": [
            {"source": "Figma Community", "price": Decimal("0"), "url": "https://figma.com/community"},
            {"source": "Creative Market", "price": Decimal("29"), "url": "https://creativemarket.com"},
        ],
    },
]

MOCK_FREELANCE_RATES: list[dict[str, Any]] = [
    {
        "item_id": "react-developer-hourly",
        "sources": [
            {"source": "Upwork (LATAM)", "price": Decimal("25"), "url": "https://upwork.com"},
            {"source": "Toptal (US client)", "price": Decimal("150"), "url": "https://toptal.com"},
        ],
    },
    {
        "item_id": "figma-design-project",
        "sources": [
            {"source": "Fiverr", "price": Decimal("50"), "url": "https://fiverr.com"},
            {"source": "99designs Contest", "price": Decimal("500"), "url": "https://99designs.com"},
        ],
    },
]


@dataclass
class ArbitrageVector:
    """Vector 2: Arbitrage Scanner.

    Detects price discrepancies across platforms, scores opportunities
    by net margin, and alerts the operator. Does NOT auto-execute
    trades unless explicitly enabled.
    """

    _enabled: bool = True
    auto_trade: bool = False  # Safety: manual by default
    min_margin_pct: float = 20.0  # Minimum 20% margin to report
    domains: list[str] = field(
        default_factory=lambda: ["domains", "digital_goods", "freelance"]
    )

    @property
    def id(self) -> VectorType:
        """Vector identifier."""
        return VectorType.ARBITRAGE

    @property
    def name(self) -> str:
        """Human-readable name."""
        return "Arbitrage Scanner"

    @property
    def enabled(self) -> bool:
        """Whether this vector is active."""
        return self._enabled

    async def scan(self) -> list[Opportunity]:
        """Scan all configured domains for arbitrage opportunities.

        Currently uses mock data sources. Replace with real APIs
        for production use.

        Returns:
            List of arbitrage opportunities above minimum margin.
        """
        all_arbs: list[ArbitrageOpportunity] = []

        if "domains" in self.domains:
            all_arbs.extend(self._scan_source(MOCK_DOMAIN_LISTINGS))
        if "digital_goods" in self.domains:
            all_arbs.extend(self._scan_source(MOCK_DIGITAL_GOODS))
        if "freelance" in self.domains:
            all_arbs.extend(self._scan_source(MOCK_FREELANCE_RATES))

        # Filter by minimum margin
        viable = [a for a in all_arbs if a.margin_pct >= self.min_margin_pct]

        opportunities: list[Opportunity] = []
        for arb in viable:
            opp = Opportunity(
                vector=VectorType.ARBITRAGE,
                title=f"Arbitrage: {arb.item_id}",
                description=(
                    f"Buy on {arb.buy.source} at €{arb.buy.price}, "
                    f"sell on {arb.sell.source} at €{arb.sell.price}. "
                    f"Net margin: €{arb.net_margin} ({arb.margin_pct:.0f}%)"
                ),
                estimated_value=arb.net_margin,
                confidence="C3",  # Mock data = C3
                effort_hours=0.5,  # Quick execution
                source_url=arb.buy.url,
                meta={
                    "buy_source": arb.buy.source,
                    "buy_price": str(arb.buy.price),
                    "sell_source": arb.sell.source,
                    "sell_price": str(arb.sell.price),
                    "margin_pct": arb.margin_pct,
                },
            )
            opportunities.append(opp)

        logger.info(
            "🔎 [ARBITRAGE] Found %d arbitrage opportunities "
            "(≥%.0f%% margin) from %d comparisons.",
            len(opportunities),
            self.min_margin_pct,
            len(all_arbs),
        )
        return opportunities

    async def execute(self, opportunity: Opportunity) -> ExecutionResult:
        """Execute an arbitrage opportunity.

        If auto_trade is disabled (default), returns a "manual action required"
        result with all the buy/sell details.

        Args:
            opportunity: The arbitrage opportunity to execute.

        Returns:
            Execution result.
        """
        if not self.auto_trade:
            logger.info(
                "⚠️ [ARBITRAGE] Manual mode: %s requires human action.",
                opportunity.title,
            )
            return ExecutionResult(
                opportunity_id=opportunity.id,
                success=True,
                revenue_actual=Decimal("0"),
                cost_actual=Decimal("0"),
                meta={
                    "action_required": "manual",
                    "buy_url": opportunity.source_url,
                    **opportunity.meta,
                },
            )

        # Auto-trade path (opt-in only)
        logger.info("🤖 [ARBITRAGE] Auto-executing: %s", opportunity.title)
        # In production: call marketplace APIs to execute the trade
        return ExecutionResult(
            opportunity_id=opportunity.id,
            success=True,
            revenue_actual=opportunity.estimated_value,
            cost_actual=Decimal(opportunity.meta.get("buy_price", "0")),
            meta={"executed_automatically": True},
        )

    def _scan_source(
        self, listings: list[dict[str, Any]]
    ) -> list[ArbitrageOpportunity]:
        """Compare prices across sources for a set of listings.

        Args:
            listings: List of items with multiple price sources.

        Returns:
            Detected arbitrage opportunities.
        """
        results: list[ArbitrageOpportunity] = []

        for item in listings:
            sources = item.get("sources", [])
            if len(sources) < 2:
                continue

            price_points = [
                PricePoint(
                    item_id=item["item_id"],
                    source=s["source"],
                    price=s["price"],
                    url=s.get("url", ""),
                )
                for s in sources
            ]

            # Find min and max
            price_points.sort(key=lambda p: p.price)
            buy = price_points[0]
            sell = price_points[-1]

            if buy.price < sell.price:
                results.append(
                    ArbitrageOpportunity(
                        item_id=item["item_id"],
                        buy=buy,
                        sell=sell,
                        fees_estimate=sell.price * Decimal("0.1"),  # 10% fee estimate
                    )
                )

        return results
