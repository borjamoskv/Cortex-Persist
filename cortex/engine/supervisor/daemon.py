# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from cortex.engine.uncategorized.endocrine import ENDOCRINE, HormoneType
from cortex.engine.uncategorized.predictive_healer import Prediction

from .types import AgentStatus

logger = logging.getLogger("cortex.supervisor")


class SupervisorDaemon:
    def __init__(self, supervisor: Any) -> None:
        self.sup = supervisor
        self.config = supervisor.config

    async def _l5_daemon(self, engine: Any = None) -> None:
        try:
            await self.sup._l5.start_daemon(engine=engine)
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as e:
            logger.error("[SUPERVISOR] L5 daemon crashed: %s", e)
            self.sup._agents["l5"].status = AgentStatus.FAILED
            self.sup._agents["l5"].error_count += 1

    async def _l6_optimization_loop(self) -> None:
        while self.sup._is_running:
            try:
                event = await self.sup._l6.optimize()
                if event.applied > 0:
                    self.sup._sync_l6_to_l5()
                    logger.info("[SUPERVISOR] L6 applied %d tunings", event.applied)
                self.sup._agents["l6"].last_heartbeat = time.monotonic()
            except (ValueError, TypeError, KeyError, OSError, RuntimeError) as e:
                logger.error("[SUPERVISOR] L6 error: %s", e)
                self.sup._agents["l6"].error_count += 1
            await asyncio.sleep(self.config.optimization_interval_s)

    async def _prediction_loop(self) -> None:
        while self.sup._is_running:
            try:
                predictions = self.sup._predictor.predict_all()
                self.sup._total_predictions += len(predictions)
                critical = [
                    p
                    for p in predictions
                    if p.is_critical and p.confidence >= self.config.preemptive_confidence
                ]
                for p in critical:
                    await self._apply_preemptive_action(p)
                self.sup._agents["predictor"].last_heartbeat = time.monotonic()
            except (ValueError, TypeError, KeyError, OSError, RuntimeError) as e:
                logger.error("[SUPERVISOR] Prediction error: %s", e)
                self.sup._agents["predictor"].error_count += 1
            await asyncio.sleep(self.config.prediction_interval_s)

    async def _health_check_loop(self) -> None:
        while self.sup._is_running:
            try:
                for _key, info in self.sup._agents.items():
                    if info.status == AgentStatus.RUNNING:
                        staleness = time.monotonic() - info.last_heartbeat
                        if staleness > self.config.health_check_interval_s * 5:
                            info.status = AgentStatus.DEGRADED
                            logger.warning(
                                "[SUPERVISOR] %s heartbeat stale (%.0fs)", info.name, staleness
                            )
                cortisol = ENDOCRINE.get_level(HormoneType.CORTISOL)
                if cortisol > self.config.cortisol_alarm:
                    logger.warning("[SUPERVISOR] System cortisol alarm: %.3f", cortisol)
            except (ValueError, TypeError, KeyError, OSError, RuntimeError) as e:
                logger.error("[SUPERVISOR] Health check error: %s", e)
            await asyncio.sleep(self.config.health_check_interval_s)

    async def _persist_loop(self) -> None:
        while self.sup._is_running:
            try:
                all_params = self.sup._l6.get_all_tuned_params()
                if all_params:
                    self.sup._store.snapshot(all_params, self.sup._l6.stats)
            except (ValueError, TypeError, KeyError, OSError, RuntimeError) as e:
                logger.error("[SUPERVISOR] Persist error: %s", e)
            await asyncio.sleep(self.config.persist_interval_s)

    async def _sync_loop(self) -> None:
        while self.sup._is_running:
            self.sup._sync_l6_to_l5()
            await asyncio.sleep(self.config.heartbeat_interval_s)

    async def _apply_preemptive_action(self, prediction: Prediction) -> None:
        action = prediction.recommended_action
        sub = prediction.subsystem
        logger.warning(
            "[SUPERVISOR] Preemptive: %s on '%s' (conf=%.2f, TTF=%.0fs)",
            action,
            sub,
            prediction.confidence,
            prediction.estimated_time_to_failure_s,
        )

        if action == "PREEMPTIVE_BATCH_REDUCTION":
            current = self.sup._l6.get_tuned_batch_size(sub)
            new_val = max(1, int(current * 0.7))
            self.sup._l6._tuned_params.setdefault(sub, {})["batch_size"] = new_val
        elif action == "PREEMPTIVE_TIMEOUT_INCREASE":
            current = self.sup._l6.get_tuned_timeout(sub)
            new_val = min(60000, current * 1.3)
            self.sup._l6._tuned_params.setdefault(sub, {})["timeout_ms"] = new_val
        elif action == "PREEMPTIVE_CONSOLIDATION":
            ENDOCRINE.pulse(HormoneType.SEROTONIN, 0.1, reason="Preemptive consolidation trigger")
        elif action == "PREEMPTIVE_BREAKER_WARMUP":
            self.sup._l5._get_or_create_breaker(sub)

        self.sup._total_preemptive_actions += 1
        self.sup._predictor.record_prevention()
        self.sup._sync_l6_to_l5()
