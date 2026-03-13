"""Apotheosis Background Audits & Math Mixin (Level 7)."""

import asyncio
import logging
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any

from cortex.engine.endocrine import ENDOCRINE, HormoneType
from cortex.engine.manifestation import manifest_singularity

if TYPE_CHECKING:
    pass

logger = logging.getLogger("cortex.engine.apotheosis.audits")


class ApotheosisAuditsMixin:
    """Mixin for background audits, REM operations, and singularity checks."""

    async def _check_singularity_state(self, dopamine: float, growth: float) -> None:
        if dopamine > 0.9 and growth > 0.8:
            logger.warning("🌌 [SINGULARITY-Ω] High Coherent.")
            # Ω₃: Verify compliance before manifestation (O(1) async check)
            if hasattr(self, "_trust") and self._trust:
                stats = await asyncio.to_thread(self._trust.get_compliance_stats)
                if stats.eu_ai_act_score < 0.8:
                    logger.error(
                        "🛡️ [TRUST] Compliance score too low for Singularity: %.2f",
                        stats.eu_ai_act_score,
                    )
                    return
            await manifest_singularity(getattr(self, "_signal_bus", None))

    async def _sync_notebooklm(self) -> None:
        """Sincroniza el Master Digest con NotebookLM (Ω₂)."""
        if not hasattr(self, "_notebooklm") or not self._notebooklm:
            return
        try:
            digest = await self._notebooklm.generate_digest()
            digest_path = Path("notebooklm_sources/master_digest.md")
            digest_path.parent.mkdir(parents=True, exist_ok=True)
            digest_path.write_text(digest)

            # Sync to cloud if detected
            cloud_target = self._notebooklm.sync_to_cloud(digest_path)
            logger.info("📓 [NOTEBOOKLM] Digest synced to cloud: %s", cloud_target)
        except (OSError, AttributeError, sqlite3.Error, asyncio.CancelledError) as e:
            logger.debug("[NOTEBOOKLM] Sync failed: %s", e)

    async def _metamemory_audit(self) -> None:
        """Evaluate Brier Score calibration during REM cycle (Ω₅)."""
        if not hasattr(self, "_cortex") or not self._cortex:
            return

        await asyncio.sleep(0)  # Async-native (Ω₁)
        try:
            manager = getattr(self._cortex, "_memory_manager", None)
            if not manager or not hasattr(manager, "metamemory"):
                return

            # 1. Global Calibration Check (Ω₂)
            global_score = manager.metamemory.calibration_score()
            if global_score != -1.0:
                if global_score > 0.25:
                    ENDOCRINE.pulse(HormoneType.CORTISOL, +0.05, reason="GlobalCalibrationDrift")
                    logger.warning("🧠 [METAMEMORY] Global Drift detected: %.2f", global_score)
                else:
                    logger.debug("🧠 [METAMEMORY] Global Calibration: %.2f", global_score)

            # 2. Domain-Specific Monitoring (Ω₅) - Per Project
            # Introspection of existing outcomes to detect specific domain ignorance
            outcomes = getattr(manager.metamemory, "_outcomes", [])
            projects = {o.project_id for o in outcomes} if outcomes else set()

            for pid in projects:
                p_score = manager.metamemory.calibration_score(project_id=pid)
                if p_score > 0.35:  # Stricter threshold for domain drift
                    ENDOCRINE.pulse(HormoneType.CORTISOL, +0.05, reason=f"DomainDrift:{pid}")
                    logger.warning("🧠 [METAMEMORY] Domain Drift in [%s]: %.2f", pid, p_score)
                elif p_score != -1.0:
                    logger.debug("🧠 [METAMEMORY] Domain [%s] Calibration: %.2f", pid, p_score)

        except (AttributeError, sqlite3.Error) as e:
            logger.error("[METAMEMORY] Audit failure: %s", e)

    async def _oracle_audit(self) -> None:
        """Ejecuta la auditoría de olvido en segundo plano (Ω₅)."""
        if not getattr(self, "_cortex", None):
            return
        try:
            from cortex.engine.forgetting_oracle import ForgettingOracle

            if getattr(self, "_oracle", None) is None:
                # Obtener referencia al caché del motor optimizado si existe
                cache_ref = getattr(self._cortex, "_cache", None)
                # Pass L1 reference so Oracle reads real access frequency data,
                # not the transaction-count approximation ghost (Ω₁ + Ω₂).
                self._oracle = ForgettingOracle(
                    self._cortex,
                    cache_ref=cache_ref,
                    l1_ref=getattr(self, "_memory_l1", None),
                )

            report = await self._oracle.evaluate(window=100)
            if report.regret_rate > ForgettingOracle.REGRET_THRESHOLD:
                from cortex.engine.forgetting_models import PolicyRecommendation

                if report.recommendation == PolicyRecommendation.PROTECT_CAUSAL_ROOTS:
                    ENDOCRINE.pulse(
                        HormoneType.CORTISOL,
                        +0.25,
                        reason=f"CausalRootThreat:{report.regret_rate:.0%}",
                    )
                    logger.critical(
                        "🛡️ [ORACLE] CAUSAL ROOT THREAT (%.0f%%). "
                        "Evicting structural ancestors. Cortisol +25%%.",
                        report.regret_rate * 100,
                    )
                else:
                    ENDOCRINE.pulse(
                        HormoneType.CORTISOL,
                        +0.15,
                        reason=f"MemoryRegret:{report.regret_rate:.0%}",
                    )
                    logger.warning(
                        "🔮 [ORACLE] High regret (%.0f%%). Policy: %s.",
                        report.regret_rate * 100,
                        report.recommendation.value,
                    )
            else:
                ENDOCRINE.pulse(HormoneType.DOPAMINE, +0.05)
        except (AttributeError, sqlite3.Error, asyncio.CancelledError) as e:
            logger.debug("[ORACLE] Audit skipped: %s", e)
        except Exception as e:  # noqa: BLE001 — intentional re-raise after logging
            logger.error("[ORACLE] Unexpected audit failure: %s", e)
            raise

    def _apply_hormonal_shifts(self, adrenaline: float, cortisol: float, dopamine: float) -> float:
        inertia = 1.0 - getattr(self, "_cognitive_weight", 0.0)
        base_sleep = (
            0.0 if adrenaline > 0.5 else getattr(self, "_SLEEP_MIN", 0.1) * max(0.1, inertia)
        )
        if adrenaline <= 0.5 and cortisol > 0.8:
            ENDOCRINE.pulse(HormoneType.CORTISOL, -0.1)
        if adrenaline < 0.2 and cortisol > 0.4:
            ENDOCRINE.pulse(HormoneType.CORTISOL, -0.05 * (1.0 + dopamine))
        return base_sleep

    def _calc_recovery(
        self,
        entropy_found: bool,
        consecutive_clean: int,
        base_sleep: float,
        growth: float,
        dopamine: float,
        cortisol: float,
    ) -> tuple[int, float]:
        if entropy_found:
            consecutive_clean = 0
            r_factor = 1.0 + (dopamine * 0.5)
            # After reset: base_sleep * (1.0 + growth) * r_factor
            # The exponential only kicks in on subsequent clean rounds below.
            derived_sleep = min(
                base_sleep * (1.0 + growth) * r_factor, getattr(self, "_SLEEP_MAX", 60.0)
            )
        else:
            consecutive_clean = min(consecutive_clean + 1, 8)
            ENDOCRINE.pulse(HormoneType.DOPAMINE, 0.02)
            ENDOCRINE.pulse(HormoneType.NEURAL_GROWTH, 0.01)
            ENDOCRINE.pulse(HormoneType.CORTISOL, -0.02)
            derived_sleep = base_sleep * (1.0 - cortisol)
        return consecutive_clean, derived_sleep

    def _calc_duration(self, derived_sleep: float, adrenaline: float, _random: Any) -> float:
        final_sleep = derived_sleep * (1.0 - adrenaline)
        q_jitter = final_sleep * getattr(self, "_SLEEP_JITTER", 0.05) * (1.0 + _random.random())
        # KAIROS-Ω: Lowered floor for high-adrenaline states
        floor = 0.05 if adrenaline > 0.8 else (0.5 if adrenaline > 0.3 else 1.0)
        return max(floor, final_sleep + _random.uniform(-q_jitter, q_jitter))
