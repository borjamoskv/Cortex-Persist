"""moneytv-1 Trading Bot Architecture v1.1 - Risk Management.

Con circuit breakers y risk management militar.
Decimal-precision. Zero tolerance for float drift.
"""

from __future__ import annotations
from typing import Optional

import logging
import threading
import time
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum, auto

log = logging.getLogger(__name__)


class Signal(Enum):
    STRONG_BUY = auto()
    BUY = auto()
    NEUTRAL = auto()
    SELL = auto()
    STRONG_SELL = auto()
    EMERGENCY_EXIT = auto()  # Liquidación total


@dataclass(frozen=True)
class Position:
    """Inmutable position descriptor."""

    __slots__ = (
        "symbol",
        "side",
        "entry_price",
        "size",
        "stop_loss",
        "take_profit",
        "max_hold_time",
        "timestamp",
        "correlation_id",
    )
    symbol: str
    side: str  # "long" | "short"
    entry_price: Decimal
    size: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    max_hold_time: int  # horas máximas
    timestamp: float
    correlation_id: str  # Para tracking de correlaciones


@dataclass
class Portfolio:
    """Snapshot del estado del portfolio en un instante."""

    total_equity: Decimal
    daily_pnl: Decimal
    peak_equity: Decimal
    positions: list[Position] = field(default_factory=list)

    @property
    def current_drawdown(self) -> Decimal:
        """Drawdown actual respecto al pico histórico."""
        if self.peak_equity == 0:
            return Decimal("0")
        return (self.peak_equity - self.total_equity) / self.peak_equity

    @property
    def daily_loss_pct(self) -> Decimal:
        """Pérdida diaria como fracción del equity."""
        if self.total_equity == 0:
            return Decimal("0")
        return self.daily_pnl / self.total_equity


class RiskManager:
    """
    Gestión de riesgo soberana. NUNCA se desactiva.
    Circuit breakers automáticos incluidos.
    Todos los umbrales en Decimal — zero float drift.
    """

    # Límites absolutos (Decimal — sin pérdida de precisión)
    MAX_POSITION_PCT = Decimal("0.05")  # 5% por posición
    MAX_DAILY_LOSS_PCT = Decimal("0.02")  # Stop diario -2%
    MAX_DRAWDOWN_PCT = Decimal("0.10")  # Stop total -10%
    MAX_CORRELATED: int = 3  # Máximo 3 posiciones correlacionadas
    MAX_LEVERAGE = Decimal("3.0")  # Apalancamiento máximo
    COOLDOWN_SECONDS: int = 60  # Mínimo 60s entre trades del mismo símbolo

    def __init__(self) -> None:
        self.circuit_breaker_triggered = False
        self.consecutive_rejections = 0
        self.MAX_CONSECUTIVE_REJECTIONS = 3
        self._cb_timer: Optional[threading.Timer] = None

    def approve_trade(self, position: Position, portfolio: Portfolio) -> bool:
        """Cada trade DEBE pasar por aquí. Sin excepciones."""
        if self.circuit_breaker_triggered:
            log.warning("🚨 CIRCUIT BREAKER ACTIVO. Trading pausado.")
            return False

        checks = [
            ("position_size", self._check_position_size(position, portfolio)),
            ("daily_loss", self._check_daily_loss(portfolio)),
            ("drawdown", self._check_drawdown(portfolio)),
            ("correlation", self._check_correlation(position, portfolio)),
            ("leverage", self._check_leverage(position)),
            ("cooldown", self._check_cooldown_period(position, portfolio)),
        ]

        failed = [name for name, passed in checks if not passed]

        if failed:
            self.consecutive_rejections += 1
            log.warning(
                "Trade RECHAZADO — checks fallidos: %s (consecutivos: %d/%d)",
                failed,
                self.consecutive_rejections,
                self.MAX_CONSECUTIVE_REJECTIONS,
            )
            if self.consecutive_rejections >= self.MAX_CONSECUTIVE_REJECTIONS:
                self._trigger_circuit_breaker()
            return False

        self.consecutive_rejections = max(0, self.consecutive_rejections - 1)
        log.info("Trade APROBADO: %s %s (size=%s)", position.side, position.symbol, position.size)
        return True

    def _check_position_size(self, position: Position, portfolio: Portfolio) -> bool:
        """Rechaza si la posición supera MAX_POSITION_PCT del equity total."""
        if portfolio.total_equity <= 0:
            log.warning("Equity ≤ 0, rechazando trade.")
            return False
        ratio = position.size / portfolio.total_equity
        if ratio > self.MAX_POSITION_PCT:
            log.warning(
                "Position size %.2f%% > max %.2f%%",
                float(ratio * 100),
                float(self.MAX_POSITION_PCT * 100),
            )
            return False
        return True

    def _check_daily_loss(self, portfolio: Portfolio) -> bool:
        """Rechaza si la pérdida diaria supera MAX_DAILY_LOSS_PCT."""
        if portfolio.total_equity <= 0:
            return False
        loss_pct = portfolio.daily_loss_pct
        if loss_pct < -self.MAX_DAILY_LOSS_PCT:
            log.warning(
                "Daily loss %.2f%% > max -%.2f%%",
                float(loss_pct * 100),
                float(self.MAX_DAILY_LOSS_PCT * 100),
            )
            return False
        return True

    def _check_drawdown(self, portfolio: Portfolio) -> bool:
        """Rechaza si el drawdown acumulado supera MAX_DRAWDOWN_PCT."""
        dd = portfolio.current_drawdown
        if dd > self.MAX_DRAWDOWN_PCT:
            log.warning(
                "Drawdown %.2f%% > max %.2f%%",
                float(dd * 100),
                float(self.MAX_DRAWDOWN_PCT * 100),
            )
            return False
        return True

    def _check_correlation(self, position: Position, portfolio: Portfolio) -> bool:
        """Rechaza si ya hay MAX_CORRELATED posiciones del mismo símbolo."""
        same_symbol = sum(1 for p in portfolio.positions if p.symbol == position.symbol)
        if same_symbol >= self.MAX_CORRELATED:
            log.warning(
                "Correlación: %d posiciones de %s (max %d)",
                same_symbol,
                position.symbol,
                self.MAX_CORRELATED,
            )
            return False
        return True

    def _check_leverage(self, position: Position) -> bool:
        """Rechaza si el apalancamiento implícito supera MAX_LEVERAGE."""
        if position.size <= 0 or position.entry_price <= 0:
            return False
        # Leverage = notional / margin (size is margin, entry_price * size = notional)
        # Simplified: if position explicitly carries leverage info, check it.
        # For now, we check if size * entry_price / size > MAX_LEVERAGE conceptually.
        # The real check: position.size is the margin; notional = entry_price * contracts.
        # We approximate: if the stop distance is tighter than 1/MAX_LEVERAGE, leverage is too high.
        risk_per_unit = abs(position.entry_price - position.stop_loss)
        if risk_per_unit == 0:
            log.warning("Stop loss = entry price, apalancamiento infinito.")
            return False
        effective_leverage = position.entry_price / risk_per_unit
        if effective_leverage > self.MAX_LEVERAGE:
            log.warning(
                "Leverage efectivo %.1fx > max %.1fx",
                float(effective_leverage),
                float(self.MAX_LEVERAGE),
            )
            return False
        return True

    def _check_cooldown_period(
        self,
        position: Position,
        portfolio: Portfolio,
    ) -> bool:
        """Rechaza si hay una posición del mismo símbolo abierta hace < COOLDOWN_SECONDS."""
        now = time.time()
        for p in portfolio.positions:
            if p.symbol == position.symbol:
                elapsed = now - p.timestamp
                if elapsed < self.COOLDOWN_SECONDS:
                    log.warning(
                        "Cooldown: %s abierta hace %.0fs (min %ds)",
                        position.symbol,
                        elapsed,
                        self.COOLDOWN_SECONDS,
                    )
                    return False
        return True

    def _trigger_circuit_breaker(self, reset_seconds: int = 86400) -> None:
        """Pausa trading por reset_seconds después de N rechazos consecutivos."""
        self.circuit_breaker_triggered = True
        log.critical(
            "🚨 CIRCUIT BREAKER ACTIVADO. Pausa de %dh.",
            reset_seconds // 3600,
        )
        # Auto-reset via background thread
        if self._cb_timer is not None:
            self._cb_timer.cancel()
        self._cb_timer = threading.Timer(
            reset_seconds,
            self._reset_circuit_breaker,
        )
        self._cb_timer.daemon = True
        self._cb_timer.start()

    def _reset_circuit_breaker(self) -> None:
        self.circuit_breaker_triggered = False
        self.consecutive_rejections = 0
        log.info("✅ Circuit breaker reseteado.")
