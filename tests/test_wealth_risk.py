"""Unit tests for cortex.wealth.risk — RiskManager.

Pure unit tests — no DB, no IO, no network.
"""

from __future__ import annotations

import time
from decimal import Decimal

from cortex.wealth.risk import Portfolio, Position, RiskManager

# ── Helpers ──────────────────────────────────────────────────────────


def _pos(
    symbol: str = "BTC",
    side: str = "long",
    entry: str = "50000",
    size: str = "1000",
    stop: str = "30000",
    tp: str = "55000",
    ts: float | None = None,
) -> Position:
    return Position(
        symbol=symbol,
        side=side,
        entry_price=Decimal(entry),
        size=Decimal(size),
        stop_loss=Decimal(stop),
        take_profit=Decimal(tp),
        max_hold_time=24,
        timestamp=ts or time.time(),
        correlation_id="test",
    )


def _portfolio(
    equity: str = "100000",
    daily_pnl: str = "0",
    peak: str | None = None,
    positions: list[Position] | None = None,
) -> Portfolio:
    return Portfolio(
        total_equity=Decimal(equity),
        daily_pnl=Decimal(daily_pnl),
        peak_equity=Decimal(peak or equity),
        positions=positions or [],
    )


# ── Position size ────────────────────────────────────────────────────


class TestPositionSize:
    def test_approve_within_limit(self):
        rm = RiskManager()
        pos = _pos(size="4000")  # 4% of 100k → under 5%
        assert rm.approve_trade(pos, _portfolio()) is True

    def test_reject_oversized(self):
        rm = RiskManager()
        pos = _pos(size="6000")  # 6% of 100k → over 5%
        assert rm.approve_trade(pos, _portfolio()) is False

    def test_reject_zero_equity(self):
        rm = RiskManager()
        assert rm.approve_trade(_pos(), _portfolio(equity="0")) is False


# ── Daily loss ───────────────────────────────────────────────────────


class TestDailyLoss:
    def test_approve_normal_day(self):
        rm = RiskManager()
        pos = _pos(size="1000")
        pf = _portfolio(daily_pnl="-1000")  # -1% → under 2%
        assert rm.approve_trade(pos, pf) is True

    def test_reject_bad_day(self):
        rm = RiskManager()
        pos = _pos(size="1000")
        pf = _portfolio(daily_pnl="-3000")  # -3% → over 2%
        assert rm.approve_trade(pos, pf) is False


# ── Drawdown ─────────────────────────────────────────────────────────


class TestDrawdown:
    def test_approve_small_drawdown(self):
        rm = RiskManager()
        pos = _pos(size="1000")
        pf = _portfolio(equity="95000", peak="100000")  # 5% DD → under 10%
        assert rm.approve_trade(pos, pf) is True

    def test_reject_large_drawdown(self):
        rm = RiskManager()
        pos = _pos(size="1000")
        pf = _portfolio(equity="85000", peak="100000")  # 15% DD → over 10%
        assert rm.approve_trade(pos, pf) is False


# ── Correlation ──────────────────────────────────────────────────────


class TestCorrelation:
    def test_approve_few_positions(self):
        rm = RiskManager()
        old_ts = time.time() - 3600  # 1h ago — past cooldown
        existing = [_pos(symbol="BTC", ts=old_ts) for _ in range(2)]
        pos = _pos(symbol="BTC", size="1000")
        assert rm.approve_trade(pos, _portfolio(positions=existing)) is True

    def test_reject_too_many_same_symbol(self):
        rm = RiskManager()
        existing = [_pos(symbol="BTC") for _ in range(3)]
        pos = _pos(symbol="BTC", size="1000")
        assert rm.approve_trade(pos, _portfolio(positions=existing)) is False


# ── Leverage ─────────────────────────────────────────────────────────


class TestLeverage:
    def test_approve_low_leverage(self):
        rm = RiskManager()
        # entry=50000, stop=48000 → risk=2000 → leverage=25x → FAIL
        # entry=50000, stop=30000 → risk=20000 → leverage=2.5x → OK
        pos = _pos(entry="50000", stop="30000", size="1000")
        assert rm.approve_trade(pos, _portfolio()) is True

    def test_reject_high_leverage(self):
        rm = RiskManager()
        # entry=50000, stop=49000 → risk=1000 → leverage=50x → FAIL
        pos = _pos(entry="50000", stop="49000", size="1000")
        assert rm.approve_trade(pos, _portfolio()) is False

    def test_reject_stop_equals_entry(self):
        rm = RiskManager()
        pos = _pos(entry="50000", stop="50000", size="1000")
        assert rm.approve_trade(pos, _portfolio()) is False


# ── Circuit breaker ──────────────────────────────────────────────────


class TestCircuitBreaker:
    def test_triggers_after_max_rejections(self):
        rm = RiskManager()
        bad_pos = _pos(size="20000")  # 20% → always rejected
        pf = _portfolio()
        for _ in range(3):
            rm.approve_trade(bad_pos, pf)
        assert rm.circuit_breaker_triggered is True

    def test_blocks_all_trades_when_active(self):
        rm = RiskManager()
        rm.circuit_breaker_triggered = True
        good_pos = _pos(size="1000")
        assert rm.approve_trade(good_pos, _portfolio()) is False

    def test_approved_trade_decrements_counter(self):
        rm = RiskManager()
        rm.consecutive_rejections = 2
        good_pos = _pos(size="1000", entry="50000", stop="30000")
        rm.approve_trade(good_pos, _portfolio())
        assert rm.consecutive_rejections == 1


# ── Portfolio properties ─────────────────────────────────────────────


class TestPortfolioProperties:
    def test_current_drawdown(self):
        pf = _portfolio(equity="90000", peak="100000")
        assert pf.current_drawdown == Decimal("0.1")

    def test_drawdown_zero_peak(self):
        pf = _portfolio(equity="0", peak="0")
        assert pf.current_drawdown == Decimal("0")

    def test_daily_loss_pct(self):
        pf = _portfolio(equity="100000", daily_pnl="-2000")
        assert pf.daily_loss_pct == Decimal("-0.02")
