# [C5-REAL] Exergy-Maximized
"""
Structural Data Models for Asymmetric Arbitrage.
Enforces BABYLON-60 Epistemology for financial precision.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CortexAmount:
    """
    BABYLON-60 Epistemology (AX-011).
    Eradicates `float` and `float64`. Stores values as Base-60 scaled integers.
    Scale: 60^4 = 12,960,000 for high precision divisibility.
    """

    SCALE_FACTOR = 12960000
    raw_value: int

    @classmethod
    def from_string(cls, value: str) -> CortexAmount:
        """Parses a string safely into the Babylon-60 integer space."""
        parts = value.split(".")
        if len(parts) == 1:
            return cls(int(parts[0]) * cls.SCALE_FACTOR)

        integer_part = int(parts[0]) * cls.SCALE_FACTOR
        fraction_str = parts[1][:7]  # Limit to 7 decimal places safely
        fraction_val = int(fraction_str.ljust(7, "0"))
        
        # Scale fraction logic: fraction_val / 10^7 * SCALE_FACTOR
        fraction_scaled = (fraction_val * cls.SCALE_FACTOR) // 10000000
        return cls(integer_part + fraction_scaled)

    def to_float_lossy(self) -> float:
        """WARNING: Only use for observability. Never for state mutation."""
        return self.raw_value / self.SCALE_FACTOR

    def __add__(self, other: CortexAmount) -> CortexAmount:
        return CortexAmount(self.raw_value + other.raw_value)

    def __sub__(self, other: CortexAmount) -> CortexAmount:
        return CortexAmount(self.raw_value - other.raw_value)

    def __gt__(self, other: CortexAmount) -> bool:
        return self.raw_value > other.raw_value

    def __ge__(self, other: CortexAmount) -> bool:
        return self.raw_value >= other.raw_value


@dataclass(frozen=True)
class ArbitrageSignal:
    """
    Epistemic Node mapping a detected structural inefficiency.
    """
    signal_id: str
    asset_pair: str
    buy_venue: str
    sell_venue: str
    buy_price: CortexAmount
    sell_price: CortexAmount
    exergy_margin: CortexAmount
    timestamp_ns: int

    @classmethod
    def create(
        cls,
        asset_pair: str,
        buy_venue: str,
        sell_venue: str,
        buy_price: CortexAmount,
        sell_price: CortexAmount,
        timestamp_ns: int,
    ) -> ArbitrageSignal:
        margin = sell_price - buy_price
        
        # Deterministic hashing of the signal
        payload = json.dumps(
            {
                "asset": asset_pair,
                "buy": buy_venue,
                "sell": sell_venue,
                "buy_p": buy_price.raw_value,
                "sell_p": sell_price.raw_value,
                "ts": timestamp_ns,
            },
            sort_keys=True,
        ).encode("utf-8")
        signal_id = f"arb_{hashlib.sha256(payload).hexdigest()[:16]}"
        
        return cls(
            signal_id=signal_id,
            asset_pair=asset_pair,
            buy_venue=buy_venue,
            sell_venue=sell_venue,
            buy_price=buy_price,
            sell_price=sell_price,
            exergy_margin=margin,
            timestamp_ns=timestamp_ns,
        )

    @property
    def is_profitable(self) -> bool:
        return self.exergy_margin.raw_value > 0
