"""
ALMA: The Sovereign Bio-Digital Soul.
Core Engine for mapping real-world system telemetry and memory events into
biological psychological states for the ALMA ecosystem.
"""

import logging
import time
from dataclasses import asdict, dataclass
from typing import Any

import aiosqlite

from cortex.config import DB_PATH
from cortex.telemetry.metrics import metrics

logger = logging.getLogger(__name__)


@dataclass
class SoulState:
    """The psychological state of the digital soul."""

    anxiety: float  # 0.0 - 1.0 (Ledger violations, errors)
    energy: float  # 0.0 - 1.0 (Throughput, active tasks)
    wisdom: float  # 0.0 - 1.0 (Bridge/Decision fact depth)
    synergy: float  # 0.0 - 1.0 (System health, response time)
    vibe: str  # Categorical label: "zen", "chaotic", "focused", "dormant", "overloaded"
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AlmaEngine:
    """The 'Soul Mirror' logic. Translates bits into biological signals."""

    def __init__(self, memory_manager: Any):
        self._memory = memory_manager
        self._last_state: SoulState | None = None
        self._smoothing_factor = 0.8  # EMA for state transitions

    async def pulse(self, mock_wisdom: float | None = None) -> SoulState:
        """Calculate the current soul state based on real-time metrics."""
        # 1. Anxiety: Ledger violations, HTTP 500s, Thalamus filtering
        ledger_violations = metrics._counters.get("cortex_ledger_violations_total", 0)
        http_errors = sum(v for k, v in metrics._counters.items() if 'status="5' in k)
        anxiety_raw = min(1.0, (ledger_violations * 0.15) + (http_errors * 0.1))

        # 2. Energy: Request throughput, background tasks
        requests = metrics._counters.get("cortex_http_requests_total", 0)
        bg_tasks = (
            len(self._memory._background_tasks) if hasattr(self._memory, "_background_tasks") else 0
        )
        energy_raw = min(1.0, (requests / 150.0) + (bg_tasks / 15.0))

        # 3. Wisdom: Facts stored in L2/L3 (Bridges, Decisions)
        wisdom_raw = mock_wisdom if mock_wisdom is not None else await self._calculate_wisdom()

        # 4. Synergy: Success rate, latency
        synergy_raw = self._calculate_synergy()

        # Combine and Smooth
        state = self._apply_smoothing(anxiety_raw, energy_raw, wisdom_raw, synergy_raw)
        self._last_state = state

        logger.debug(
            "ALMA Pulse: %s (A:%.2f, E:%.2f, W:%.2f, S:%.2f)",
            state.vibe,
            state.anxiety,
            state.energy,
            state.wisdom,
            state.synergy,
        )
        return state

    async def _calculate_wisdom(self) -> float:
        """Estimate wisdom based on high-value facts."""
        try:
            # Connect to DB and count bridges/decisions
            async with aiosqlite.connect(DB_PATH) as db:
                query = (
                    "SELECT COUNT(*) FROM memory_events "
                    "WHERE metadata LIKE '%bridge%' OR metadata LIKE '%decision%'"
                )
                cursor = await db.execute(query)
                row = await cursor.fetchone()
                count = row[0] if row else 0
                return min(1.0, count / 50.0)  # 50 = Master level (L5)
        except (aiosqlite.Error, OSError):
            return 0.0

    def _calculate_synergy(self) -> float:
        """Calculate system synergy (health + speed)."""
        success_reqs = sum(v for k, v in metrics._counters.items() if 'status="2' in k)
        total_reqs = metrics._counters.get("cortex_http_requests_total", 0)
        if total_reqs == 0:
            return 1.0
        uptime_ratio = success_reqs / total_reqs
        return min(1.0, uptime_ratio)

    def _determine_vibe(self, anxiety: float, energy: float, wisdom: float) -> str:
        if anxiety > 0.6:
            return "chaotic"
        if energy > 0.85:
            return "overloaded"
        if wisdom > 0.7 and anxiety < 0.2:
            return "zen"
        if energy > 0.3:
            return "focused"
        if energy < 0.15:
            return "dormant"
        return "neutral"

    def _apply_smoothing(self, a: float, e: float, w: float, s: float) -> SoulState:
        """Apply Exponential Moving Average for fluid state transitions."""
        if self._last_state is None:
            res_a, res_e, res_w, res_s = a, e, w, s
        else:
            sf = self._smoothing_factor
            res_a = (self._last_state.anxiety * sf) + (a * (1 - sf))
            res_e = (self._last_state.energy * sf) + (e * (1 - sf))
            res_w = (self._last_state.wisdom * sf) + (w * (1 - sf))
            res_s = (self._last_state.synergy * sf) + (s * (1 - sf))

        vibe = self._determine_vibe(res_a, res_e, res_w)

        return SoulState(
            anxiety=round(res_a, 4),
            energy=round(res_e, 4),
            wisdom=round(res_w, 4),
            synergy=round(res_s, 4),
            vibe=vibe,
            timestamp=time.time(),
        )
