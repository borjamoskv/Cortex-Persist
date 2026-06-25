# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from legacy_research.extensions.llm._hedging import HedgedRequestStrategy
from legacy_research.extensions.llm._models import CascadeEvent, CascadeTier
from legacy_research.utils.result import Ok

if TYPE_CHECKING:
    from legacy_research.extensions.llm._cascade import CascadeManager
    from legacy_research.extensions.llm._models import BaseProvider, CortexPrompt
    from legacy_research.extensions.llm._telemetry import CascadeTelemetry
    from legacy_research.utils.result import Result

logger = logging.getLogger("cortex.extensions.llm._router_hedging")


async def execute_hedged(
    prompt: CortexPrompt,
    hedging_providers: list[BaseProvider],
    cascade: CascadeManager,
    telemetry: CascadeTelemetry,
) -> Result[str, str] | None:
    """Attempt hedged (parallel) execution if peers are available."""
    if not hedging_providers:
        return None

    active_hedgers = [
        p for p in hedging_providers if not cascade.is_nxdomain_cached(p.provider_name)
    ]
    if not active_hedgers:
        return None

    result_hedge, errors = await HedgedRequestStrategy.race(active_hedgers, prompt)
    if result_hedge:
        cascade.set_a_record(result_hedge.winner, result_hedge.latency_ms)
        telemetry.emit(
            CascadeEvent(
                intent=prompt.intent,
                resolved_by=result_hedge.winner,
                project=prompt.project,
                tier=CascadeTier.PRIMARY,
                depth=1,
                latency_ms=result_hedge.latency_ms,
                errors=errors,
            )
        )
        return Ok(result_hedge.response)

    for p in active_hedgers:
        cascade.set_nx_record(p.provider_name)
    return None


async def execute_swarm(
    prompt: CortexPrompt,
    primary: BaseProvider,
    fallbacks_ordered: list[BaseProvider],
    cascade: CascadeManager,
    telemetry: CascadeTelemetry,
) -> Result[str, str] | None:
    """Ω₂₁: Parallel Swarm Racing."""
    from legacy_research.extensions.llm._models import ReasoningMode

    swarm_peers = []
    reasoning_mode = getattr(prompt, "reasoning_mode", None)

    if reasoning_mode == ReasoningMode.ULTRA_THINK and getattr(primary, "tier", None) != "frontier":
        pass
    else:
        swarm_peers.append(primary)

    swarm_peers.extend(fallbacks_ordered[:2])

    active_peers = [p for p in swarm_peers if not cascade.is_nxdomain_cached(p.provider_name)]

    if len(active_peers) < 2:
        return None

    logger.info(
        "🚀 [Ω₂₁ SWARM RACE] Starting race between: %s", [p.provider_name for p in active_peers]
    )

    result_race, errors = await HedgedRequestStrategy.race(active_peers, prompt)
    if result_race:
        cascade.set_a_record(result_race.winner, result_race.latency_ms)
        telemetry.emit(
            CascadeEvent(
                intent=prompt.intent,
                resolved_by=result_race.winner,
                project=prompt.project,
                tier=CascadeTier.PRIMARY,
                depth=1,
                latency_ms=result_race.latency_ms,
                errors=errors,
            )
        )
        return Ok(result_race.response)

    return None
