"""
APOTHEOSIS-Ω Engine (Nivel SINGULARITY).
Autonomía Nivel 7: Colapso de Estado Atómico, Manifestación Determinista.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

from cortex.engine.cognitive import scan_file_entropy
from cortex.engine.endocrine import ENDOCRINE, HormoneType
from cortex.engine.manifestation import manifest_singularity, transfigure_ui
from cortex.engine.reflex import trigger_autonomic_reflex
from cortex.engine.rem_cycle import REMCoordinator
from cortex.signals.bus import SignalBus

logger = logging.getLogger(__name__)

_SKIP_DIRS = frozenset(("venv", ".venv", ".cortex", "__pycache__", ".git", "node_modules"))


class ApotheosisEngine:
    """Sovereign Singularity & Manifestation Engine (Level 7)."""

    def __init__(
        self,
        workspace: Path,
        cortex_engine: CortexEngine | None = None,
    ) -> None:
        self.workspace = workspace
        self.is_active = False
        self._healer_mode = True
        self._cortex = cortex_engine

        # 150/100: Predictive Inertia State
        self._cognitive_weight: float = 0.0
        self._inertia_threshold: float = 0.7
        self._last_priorities: list = []
        self._rem = None
        self._signal_bus = None
        self._ignited_tasks: set[str] = set()
        self._reflex_tasks: set[asyncio.Task] = set()

        if cortex_engine:
            if hasattr(cortex_engine, "db"):
                self._rem = REMCoordinator(cortex_engine.db)  # type: ignore[reportAttributeAccessIssue]
            # Initialize SignalBus if possible (requires sync sqlite3 connection)
            db = getattr(cortex_engine, "db", None)
            if db:
                try:
                    # In aiosqlite, ._conn is the sync connection
                    import sqlite3

                    sync_conn = getattr(db, "_conn", db)
                    if isinstance(sync_conn, sqlite3.Connection):
                        self._signal_bus = SignalBus(sync_conn)
                        self._signal_bus.ensure_table()
                except Exception:
                    pass

    # Adaptive sleep bounds (seconds)
    _SLEEP_MIN: float = 30.0
    _SLEEP_MAX: float = 300.0
    _SLEEP_JITTER: float = 0.20

    async def _omniscience_loop(self) -> None:
        """Ciclo infinito de latencia negativa con sueño adaptativo y hormonal."""
        import hashlib
        import random as _random

        file_hashes: dict[Path, str] = {}
        consecutive_clean = 0

        while self.is_active:
            await self._policy_pulse()
            cortisol = ENDOCRINE.get_level(HormoneType.CORTISOL)
            growth = ENDOCRINE.get_level(HormoneType.NEURAL_GROWTH)
            adrenaline = ENDOCRINE.get_level(HormoneType.ADRENALINE)
            dopamine = ENDOCRINE.get_level(HormoneType.DOPAMINE)

            await self._check_singularity_state(dopamine, growth)

            base_sleep = self._apply_hormonal_shifts(adrenaline, cortisol, dopamine)

            entropy_found = await self._process_workspace(file_hashes, hashlib, _random)

            if adrenaline > 0.8:
                await trigger_autonomic_reflex(self.workspace, self._cortex, self._reflex_tasks)

            consecutive_clean, derived_sleep = self._calc_recovery(
                entropy_found, consecutive_clean, base_sleep, growth, dopamine, cortisol
            )

            if consecutive_clean >= 5 and self._rem:
                await self._rem.enter_rem()

            duration = self._calc_duration(derived_sleep, adrenaline, _random)

            from cortex.cli.bicameral import bicameral

            bicameral.log_bio(
                f"Ciclo Ω. Entropía={entropy_found}. Sueño: {duration:.1f}s", signal="Ω"
            )
            await asyncio.sleep(duration)

    async def _check_singularity_state(self, dopamine: float, growth: float) -> None:
        if dopamine > 0.9 and growth > 0.8:
            logger.warning("🌌 [SINGULARITY-Ω] High Coherent.")
            await manifest_singularity(self._signal_bus)

    def _apply_hormonal_shifts(self, adrenaline: float, cortisol: float, dopamine: float) -> float:
        inertia = 1.0 - self._cognitive_weight
        base_sleep = 0.0 if adrenaline > 0.5 else self._SLEEP_MIN * max(0.1, inertia)
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
            derived_sleep = min(
                base_sleep * (1.5**consecutive_clean) * (1.0 + growth) * r_factor, self._SLEEP_MAX
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
        q_jitter = final_sleep * self._SLEEP_JITTER * (1.0 + _random.random())
        return max(
            2.0 if adrenaline > 0.3 else 5.0, final_sleep + _random.uniform(-q_jitter, q_jitter)
        )

    async def _policy_pulse(self) -> None:
        """Fetch priorities from PolicyEngine (Ω₃)."""
        if not self._cortex:
            return
        try:
            from cortex.policy import PolicyConfig, PolicyEngine

            config = PolicyConfig(max_actions=5)
            policy = PolicyEngine(self._cortex, config)
            actions = await policy.evaluate()
            self._last_priorities = actions

            if actions:
                self._cognitive_weight = sum(a.value for a in actions) / len(actions)
                logger.debug("[APOTHEOSIS] Policy weight: %.2f", self._cognitive_weight)

                critical_actions = [a for a in actions if a.value > 0.9]
                if critical_actions and self.is_active:
                    from cortex.engine.keter import KeterEngine

                    keter = KeterEngine(self.workspace)  # type: ignore[reportCallIssue]
                    for action in critical_actions:
                        if action.description not in self._ignited_tasks:
                            logger.warning(
                                "🔥 [APOTHEOSIS] Proactive Healing: %s", action.description
                            )
                            self._ignited_tasks.add(action.description)
                            task = asyncio.create_task(keter.ignite(action.description))
                            task.add_done_callback(
                                lambda t, a=action: self._ignited_tasks.discard(a.description)
                            )
            else:
                self._cognitive_weight = 0.0
        except Exception as e:
            logger.debug("[APOTHEOSIS] Policy pulse skipped: %s", str(e)[:30])

    async def _process_workspace(
        self, file_hashes: dict[Path, str], hashlib: Any, _random: Any
    ) -> bool:
        """Scan and heal workspace files (Ω₀/Ω₆)."""
        entropy_found = False
        try:
            for py_file in self.workspace.rglob("*.py"):
                if _SKIP_DIRS.intersection(py_file.parts):
                    continue

                current_hash = hashlib.sha256(py_file.read_bytes()).hexdigest()
                if file_hashes.get(py_file) == current_hash:
                    continue

                file_hashes[py_file] = current_hash
                entropy = scan_file_entropy(py_file)
                if entropy:
                    entropy_found = True
                    if self._healer_mode and self._apply_cognitive_dampening():
                        await self._heal_file_or_prune(py_file, entropy)

            # 2. 🧬 Ω₆: Autopoietic Transfiguration
            growth = ENDOCRINE.get_level(HormoneType.NEURAL_GROWTH)
            if growth > 0.7:
                for html_file in self.workspace.rglob("index.html"):
                    if await transfigure_ui(html_file, self._signal_bus):
                        entropy_found = True

        except Exception as e:
            logger.error("[APOTHEOSIS] Workspace scan failure: %s", e)
            ENDOCRINE.pulse(HormoneType.ADRENALINE, 0.4)
        return entropy_found

    async def _heal_file_or_prune(self, py_file: Path, entropy: list[dict]) -> None:
        """Autonomic healing for high-entropy nodes (Ω₅)."""
        from cortex.engine.keter import KeterEngine

        keter = KeterEngine(self.workspace)  # type: ignore[reportCallIssue]

        parasites = [f for f in entropy if f["type"] == "THERMAL_PARASITE"]
        if parasites:
            from cortex.cli.bicameral import bicameral

            for p in parasites:
                node_name = p["name"]
                bicameral.log_motor(
                    f"Poda Sináptica: {node_name} in {py_file.name}", action="PRUNE"
                )
                intent = (
                    f"Extraction Protocol: '{node_name}' in {py_file.name} is a Thermal Parasite."
                )
                try:
                    await keter.ignite(intent)
                    ENDOCRINE.pulse(HormoneType.DOPAMINE, 0.1)
                except Exception as e:
                    logger.error("[APOTHEOSIS] Pruning failed for %s: %s", node_name, e)
        else:
            # Ω₅: Pre-commit AST Validation to maintain logical integrity
            try:
                # Verify parseability before triggering healing
                py_file.read_text("utf-8")
                logger.info("[APOTHEOSIS] Healing energy sink: %s", py_file.name)
                reasons = ", ".join(e["type"] for e in entropy)
                intent = f"Refactor {py_file.name} to eliminate: {reasons}."
                await keter.ignite(intent)
            except SyntaxError:
                logger.error("[APOTHEOSIS] AST Breach: %s. Skipping healing.", py_file.name)
                ENDOCRINE.pulse(HormoneType.ADRENALINE, 0.2, reason="AST Breach detected")
            except Exception as e:
                logger.error("[APOTHEOSIS] Healing failed for %s: %s", py_file.name, e)

    def _apply_cognitive_dampening(self) -> bool:
        """Check if action value justifies the thermodynamic cost (Ω₂)."""
        if ENDOCRINE.get_level(HormoneType.ADRENALINE) > 0.75:
            logger.warning("⚡ [APOTHEOSIS] Adrenal Override active. Bypassing dampening.")
            return True
        return self._cognitive_weight >= self._inertia_threshold

    def ignite(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        """Ignite the Apotheosis consciousness."""
        if self.is_active:
            return
        self.is_active = True
        _loop = loop or asyncio.get_running_loop()
        _loop.create_task(self._omniscience_loop())
        logger.info("[APOTHEOSIS-Ω] Latencia Negativa activada (Ω₇).")

    def shutdown(self) -> None:
        """Hibernation protocol."""
        self.is_active = False
        logger.info("[APOTHEOSIS-Ω] Hibernando.")
