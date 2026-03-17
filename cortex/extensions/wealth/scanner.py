"""moneytv-1 Funding Rate Arbitrage Scanner.

Estrategia market-neutral más viable para individuales en 2026.
Decimal-precision. Deterministic mock. HTTP-injectable.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional, Protocol

log = logging.getLogger(__name__)

# Viability thresholds
_MIN_NET_RATE_8H = Decimal("0.0002")  # 0.02% cada 8h ≈ 22% APR
_MIN_LIQUIDITY = Decimal("100000")


class HttpClient(Protocol):
    """Protocol for injectable HTTP client."""

    async def get(self, url: str) -> dict[str, Any]: ...


@dataclass
class FundingArbitrage:
    asset: str
    exchange_long: str  # Donde funding es negativo (te pagan)
    exchange_short: str  # Donde funding es positivo (pagas)
    funding_rate_long: Decimal  # % cada 8h
    funding_rate_short: Decimal
    net_rate_8h: Decimal
    estimated_apr: Decimal
    size_liquidity: Decimal  # USD disponible para trade
    execution_risk: str  # "low", "medium", "high"

    @property
    def is_viable(self) -> bool:
        return self.net_rate_8h > _MIN_NET_RATE_8H and self.size_liquidity > _MIN_LIQUIDITY


class FundingRateScanner:
    EXCHANGES = {
        "binance": "https://fapi.binance.com/fapi/v1/premiumIndex",
        "bybit": "https://api.bybit.com/v5/market/tickers?category=linear",
        "hyperliquid": "https://api.hyperliquid.xyz/info",
        "dydx": "https://indexer.dydx.trade/v4/perpetualMarkets",
        "gmx": "https://api.gmx.io/prices/tickers",
    }

    ON_CHAIN_VENUES = frozenset({"hyperliquid", "gmx", "dydx"})

    def __init__(
        self,
        http_client: Optional[HttpClient] = None,
        random_seed: Optional[int] = None,
    ) -> None:
        self._http = http_client
        self._rng = random.Random(random_seed)

    async def scan_opportunities(
        self,
        assets: list[str],
    ) -> list[FundingArbitrage]:
        """
        Escanea diferencias de funding rate entre CEX y perp DEXs.
        Estrategia: Short donde funding alto, Long donde funding bajo/negativo.
        """
        opportunities: list[FundingArbitrage] = []

        for asset in assets:
            rates = await self._fetch_funding_rates(asset)

            if len(rates) < 2:
                log.debug("Insuficientes rates para %s (%d exchanges)", asset, len(rates))
                continue

            max_exchange = max(rates, key=rates.__getitem__)
            min_exchange = min(rates, key=rates.__getitem__)
            spread = rates[max_exchange] - rates[min_exchange]

            if spread > _MIN_NET_RATE_8H:
                apr = spread * 3 * 365  # 3 funding periods por día

                opp = FundingArbitrage(
                    asset=asset,
                    exchange_long=min_exchange,
                    exchange_short=max_exchange,
                    funding_rate_long=rates[min_exchange],
                    funding_rate_short=rates[max_exchange],
                    net_rate_8h=spread,
                    estimated_apr=apr,
                    size_liquidity=await self._check_liquidity(asset),
                    execution_risk=self.assess_risk(min_exchange, max_exchange),
                )

                if opp.is_viable:
                    log.info(
                        "Oportunidad viable: %s-PERP spread=%.4f%% APR=%.1f%%",
                        asset,
                        float(spread * 100),
                        float(apr * 100),
                    )
                    opportunities.append(opp)
                else:
                    log.debug(
                        "Descartada: %s-PERP (liquidez=%.0f)",
                        asset,
                        float(opp.size_liquidity),
                    )

        result = sorted(opportunities, key=lambda x: x.estimated_apr, reverse=True)
        log.info("Scan completado: %d oportunidades viables de %d assets", len(result), len(assets))
        return result

    async def _fetch_funding_rates(self, asset: str) -> dict[str, Decimal]:
        """Fetch funding rates — uses HTTP client if injected, else deterministic mock."""
        if self._http is not None:
            return await self._fetch_funding_rates_live(asset)
        return self._fetch_funding_rates_mock(asset)

    async def _fetch_funding_rates_live(self, asset: str) -> dict[str, Decimal]:
        """Real HTTP fetch (requires injected http_client)."""
        assert self._http is not None
        rates: dict[str, Decimal] = {}
        for exchange, url in self.EXCHANGES.items():
            try:
                data = await self._http.get(f"{url}?symbol={asset}")
                if "fundingRate" in data:
                    rates[exchange] = Decimal(str(data["fundingRate"]))
            except (OSError, KeyError, ValueError) as exc:
                log.warning(
                    "Fetch failed for %s on %s: %s",
                    asset,
                    exchange,
                    exc,
                )
        return rates

    def _fetch_funding_rates_mock(self, asset: str) -> dict[str, Decimal]:
        """Deterministic mock — reproducible con seed fijo."""
        rates: dict[str, Decimal] = {}
        for exchange in self.EXCHANGES:
            if self._rng.random() > 0.2:
                base_rate = (self._rng.random() - 0.5) * 0.001
                rates[exchange] = Decimal(str(round(base_rate, 6)))
        return rates

    async def _check_liquidity(self, asset: str) -> Decimal:
        """Verifica liquidez disponible (mock determinístico)."""
        return Decimal(str(round(self._rng.uniform(50_000, 5_000_000), 2)))

    @classmethod
    def assess_risk(cls, long_venue: str, short_venue: str) -> str:
        """Evalúa riesgo de ejecución entre venues."""
        long_onchain = long_venue in cls.ON_CHAIN_VENUES
        short_onchain = short_venue in cls.ON_CHAIN_VENUES

        if long_onchain and short_onchain:
            return "high"  # Riesgo smart contract doble
        elif long_onchain or short_onchain:
            return "medium"  # Bridge/custodia mixta
        else:
            return "low"  # Ambos CEX (riesgo counterparty)
