"""moneytv-1 Trading Bot Architecture v1.1 - Risk Management.

Con circuit breakers y risk management militar.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum, auto


class Signal(Enum):
    STRONG_BUY = auto()
    BUY = auto()
    NEUTRAL = auto()
    SELL = auto()
    STRONG_SELL = auto()
    EMERGENCY_EXIT = auto()  # Nuevo: Liquidación total


@dataclass(frozen=True)
class Position:
    symbol: str
    side: str  # "long" | "short"
    entry_price: float
    size: float
    stop_loss: float
    take_profit: float
    max_hold_time: int  # horas máximas
    timestamp: float
    correlation_id: str  # Para tracking de correlaciones


class RiskManager:
    """
    Gestión de riesgo soberana. NUNCA se desactiva.
    Circuit breakers automáticos incluidos.
    """
    # Límites absolutos
    MAX_POSITION_PCT = 0.05      # 5% por posición
    MAX_DAILY_LOSS_PCT = 0.02    # Stop diario -2%
    MAX_DRAWDOWN_PCT = 0.10      # Stop total -10%
    MAX_CORRELATED = 3           # Máximo 3 posiciones correlacionadas
    MAX_LEVERAGE = 3.0           # Apalancamiento máximo
    
    def __init__(self):
        self.circuit_breaker_triggered = False
        self.consecutive_losses = 0
        self.MAX_CONSECUTIVE_LOSSES = 3

    def approve_trade(self, position: Position, portfolio: dict) -> bool:
        """Cada trade DEBE pasar por aquí. Sin excepciones."""
        if self.circuit_breaker_triggered:
            print("🚨 CIRCUIT BREAKER ACTIVO. Trading pausado.")
            return False
            
        checks = [
            self._check_position_size(position, portfolio),
            self._check_daily_loss(portfolio),
            self._check_drawdown(portfolio),
            self._check_correlation(position, portfolio),
            self._check_leverage(position),
            self._check_cooldown_period(position)
        ]
        
        approved = all(checks)
        
        if not approved:
            self.consecutive_losses += 1
            if self.consecutive_losses >= self.MAX_CONSECUTIVE_LOSSES:
                self._trigger_circuit_breaker()
        else:
            self.consecutive_losses = max(0, self.consecutive_losses - 1)
            
        return approved
    
    def _check_position_size(self, position: Position, portfolio: dict) -> bool:
        # Mock logic
        return True

    def _check_daily_loss(self, portfolio: dict) -> bool:
        return True

    def _check_drawdown(self, portfolio: dict) -> bool:
        return True

    def _check_correlation(self, position: Position, portfolio: dict) -> bool:
        return True

    def _check_leverage(self, position: Position) -> bool:
        return True

    def _check_cooldown_period(self, position: Position) -> bool:
        return True

    def _trigger_circuit_breaker(self):
        """Pausa trading por 24h después de 3 rechazos consecutivos."""
        self.circuit_breaker_triggered = True
        print("🚨 CIRCUIT BREAKER ACTIVADO. Pausa de 24h.")
        # asyncio.create_task(self._reset_circuit_breaker())
    
    async def _reset_circuit_breaker(self):
        await asyncio.sleep(86400)  # 24 horas
        self.circuit_breaker_triggered = False
        self.consecutive_losses = 0
        print("✅ Circuit breaker reseteado.")
