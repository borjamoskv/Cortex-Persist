"""moneytv-1 Funding Rate Arbitrage Scanner.

Estrategia market-neutral más viable para individuales en 2026.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class FundingArbitrage:
    asset: str
    exchange_long: str  # Donde funding es negativo (te pagan)
    exchange_short: str # Donde funding es positivo (pagas)
    funding_rate_long: float  # % cada 8h
    funding_rate_short: float
    net_rate_8h: float
    estimated_apr: float
    size_liquidity: float  # USD disponible para trade
    execution_risk: str  # "low", "medium", "high"
    
    @property
    def is_viable(self) -> bool:
        # Mínimo 0.02% cada 8h = ~22% APR
        return self.net_rate_8h > 0.0002 and self.size_liquidity > 100_000


class FundingRateScanner:
    EXCHANGES = {
        "binance": "https://fapi.binance.com/fapi/v1/premiumIndex",
        "bybit": "https://api.bybit.com/v5/market/tickers?category=linear",
        "hyperliquid": "https://api.hyperliquid.xyz/info",  # Nuevo líder 2026
        "dydx": "https://indexer.dydx.trade/v4/perpetualMarkets",
        "gmx": "https://api.gmx.io/prices/tickers"  # On-chain
    }
    
    async def scan_opportunities(self, assets: List[str]) -> List[FundingArbitrage]:
        """
        Escanea diferencias de funding rate entre CEX y perp DEXs.
        Estrategia: Short donde funding alto, Long donde funding bajo/negativo.
        """
        opportunities = []
        
        for asset in assets:
            rates = await self._fetch_funding_rates(asset)
            
            if len(rates) >= 2:
                # Encontrar máximo y mínimo
                max_rate = max(rates.items(), key=lambda x: x[1])
                min_rate = min(rates.items(), key=lambda x: x[1])
                
                spread = max_rate[1] - min_rate[1]
                
                # Si el spread es > 0.02% cada 8h (22% APR potencial)
                if spread > 0.0002:
                    apr = spread * 3 * 365  # 3 funding periods por día
                    
                    opp = FundingArbitrage(
                        asset=asset,
                        exchange_long=min_rate[0],  # Recibes funding
                        exchange_short=max_rate[0], # Pagas funding
                        funding_rate_long=min_rate[1],
                        funding_rate_short=max_rate[1],
                        net_rate_8h=spread,
                        estimated_apr=apr,
                        size_liquidity=await self._check_liquidity(asset),
                        execution_risk=self._assess_risk(min_rate[0], max_rate[0])
                    )
                    
                    if opp.is_viable:
                        opportunities.append(opp)
        
        return sorted(opportunities, key=lambda x: x.estimated_apr, reverse=True)
    
    async def _fetch_funding_rates(self, asset: str) -> Dict[str, float]:
        """Simulate fetching funding rates from multiple exchanges."""
        # En una integración real, aquí habría llamadas HTTP (aiohttp) a las APIs.
        # Por ahora usaremos datos mockeados para demostración.
        import random
        
        # Generar rates aleatorios para la simulación
        # Rate típico suele oscilar entre -0.05% y 0.05% cada 8h
        rates = {}
        for exchange in self.EXCHANGES.keys():
            # Algunos exchanges no listan todo
            if random.random() > 0.2:
                # Generar rate en base a 10000 para mayor precisión
                # Ej: 0.01% = 0.0001
                base_rate = (random.random() - 0.5) * 0.001
                rates[exchange] = base_rate
                
        return rates

    async def _check_liquidity(self, asset: str) -> float:
        """Verifica liquidez disponible simulada."""
        import random
        return random.uniform(50_000, 5_000_000)

    def _assess_risk(self, long_venue: str, short_venue: str) -> str:
        """Evalúa riesgo de ejecución entre venues."""
        on_chain = ["hyperliquid", "gmx", "dydx"]
        
        if long_venue in on_chain and short_venue in on_chain:
            return "high"  # Riesgo smart contract
        elif long_venue in on_chain or short_venue in on_chain:
            return "medium"  # Riesgo de bridge/custodia mixta
        else:
            return "low"  # Ambos CEX (riesgo counterparty)
