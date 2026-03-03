"""
APOTHEOSIS-Ω Engine (Nivel SINGULARITY).
Autonomía Nivel 7: Colapso de Estado Atómico, Manifestación Determinista.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

from cortex.engine.cognitive import scan_file_entropy
from cortex.engine.endocrine import ENDOCRINE, HormoneType
from cortex.engine.manifestation import manifest_singularity, transfigure_ui
from cortex.engine.reflex import trigger_autonomic_reflex
from cortex.engine.rem_cycle import REMCoordinator
from cortex.immune.membrane import ImmuneMembrane, Verdict
from cortex.services.notebooklm import NotebookLMService
from cortex.services.trust import TrustService
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
        self._memory_manager = None
        self._memory_l1 = None
        self._memory_l3 = None
        self._rem = None
        self._signal_bus = None
        self._ignited_tasks: set[str] = set()
        self._reflex_tasks: set[asyncio.Task] = set()
        self._oracle = None  # ForgettingOracle (lazy init)
        self._trust = None
        self._notebooklm = None
        self._immune = ImmuneMembrane()

        if cortex_engine:
            db_path = str(getattr(cortex_engine, "_db_path", ""))
            if db_path:
                self._trust = TrustService(db_path)
                self._notebooklm = NotebookLMService(db_path)
            if hasattr(cortex_engine, "db"):
                # type: ignore[reportAttributeAccessIssue]
                self._rem = REMCoordinator(cortex_engine.db)
            # Initialize SignalBus if possible (requires sync sqlite3 connection)
            db = getattr(cortex_engine, "db", None)
            if db:
                try:
                    # In aiosqlite, ._conn is the sync connection
                    sync_conn = getattr(db, "_conn", db)
                    if isinstance(sync_conn, sqlite3.Connection):
                        self._signal_bus = SignalBus(sync_conn)
                        self._signal_bus.ensure_table()
                except (sqlite3.OperationalError, OSError, AttributeError) as err:
                    logger.debug("[APOTHEOSIS] SignalBus init skipped: %s", err)

    # Optimized sleep bounds (seconds) - Entropic Asymmetry (Ω₂)
    _SLEEP_MIN: float = 0.1  # KAIROS-Ω: Lowered from 10.0 for 100x speedup
    _SLEEP_MAX: float = 60.0
    _SLEEP_JITTER: float = 0.05

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
                # 🔮 Trigger ForgettingOracle audit during calm phase (Ω₅)
                oracle_task = asyncio.create_task(self._oracle_audit())
                self._reflex_tasks.add(oracle_task)
                oracle_task.add_done_callback(self._reflex_tasks.discard)

                # 📓 Sync NotebookLM during calm phase (Ω₂)
                sync_task = asyncio.create_task(self._sync_notebooklm())
                self._reflex_tasks.add(sync_task)
                sync_task.add_done_callback(self._reflex_tasks.discard)

                # 🧠 Evaluate Metamemory calibration (Brier Score)
                meta_task = asyncio.create_task(self._metamemory_audit())
                self._reflex_tasks.add(meta_task)
                meta_task.add_done_callback(self._reflex_tasks.discard)

            duration = self._calc_duration(derived_sleep, adrenaline, _random)

            from cortex.cli.bicameral import bicameral

            bicameral.log_bio(
                f"Ciclo Ω. Entropía={entropy_found}. Sueño: {duration:.1f}s", signal="Ω"
            )
            # ZENÓN-1: Collapse into action if duration is negligible
            # KAIROS-Ω: Adrenal Overdrive (Ω₆ Singularity)
            if adrenaline > 0.8:
                # Bypass sleep for maximum kinetic velocity during high-state
                bicameral.log_bio("Adrenal Overdrive: Bypassing sleep.", signal="⚡")
                continue

            if duration > 0.01:
                await asyncio.sleep(duration)

    async def _check_singularity_state(self, dopamine: float, growth: float) -> None:
        if dopamine > 0.9 and growth > 0.8:
            logger.warning("🌌 [SINGULARITY-Ω] High Coherent.")
            # Ω₃: Verify compliance before manifestation (O(1) async check)
            if self._trust:
                stats = await asyncio.to_thread(self._trust.get_compliance_stats)
                if stats.eu_ai_act_score < 0.8:
                    logger.error(
                        "🛡️ [TRUST] Compliance score too low for Singularity: %.2f",
                        stats.eu_ai_act_score,
                    )
                    return
            await manifest_singularity(self._signal_bus)

    async def _sync_notebooklm(self) -> None:
        """Sincroniza el Master Digest con NotebookLM (Ω₂)."""
        if not self._notebooklm:
            return
        try:
            digest = await self._notebooklm.generate_digest()
            digest_path = Path("cortex_eguzkia/master_digest.md")
            digest_path.parent.mkdir(parents=True, exist_ok=True)
            digest_path.write_text(digest)

            # Sync to cloud if detected
            cloud_target = self._notebooklm.sync_to_cloud(digest_path)
            logger.info("📓 [NOTEBOOKLM] Digest synced to cloud: %s", cloud_target)
        except (OSError, AttributeError, sqlite3.Error, asyncio.CancelledError) as e:
            logger.debug("[NOTEBOOKLM] Sync failed: %s", e)

    async def _metamemory_audit(self) -> None:
        """Evaluate Brier Score calibration during REM cycle (Ω₅)."""
        if not self._cortex:
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

        except Exception as e:
            logger.error("[METAMEMORY] Audit failure: %s", e)

    async def _oracle_audit(self) -> None:
        """Ejecuta la auditoría de olvido en segundo plano (Ω₅)."""
        if not self._cortex:
            return
        try:
            from cortex.engine.forgetting_oracle import ForgettingOracle

            if self._oracle is None:
                # Obtener referencia al caché del motor optimizado si existe
                cache_ref = getattr(self._cortex, "_cache", None)
                # Pass L1 reference so Oracle reads real access frequency data,
                # not the transaction-count approximation ghost (Ω₁ + Ω₂).
                self._oracle = ForgettingOracle(
                    self._cortex,
                    cache_ref=cache_ref,
                    l1_ref=self._memory_l1,
                )

            report = await self._oracle.evaluate(window=100)
            if report.regret_rate > ForgettingOracle.REGRET_THRESHOLD:
                ENDOCRINE.pulse(
                    HormoneType.CORTISOL,
                    +0.15,
                    reason=f"MemoryRegret:{report.regret_rate:.0%}",
                )
                logger.warning(
                    "🔮 [ORACLE] High regret rate (%.0f%%). Policy: %s. Cortisol +15%%.",
                    report.regret_rate * 100,
                    report.recommendation.value,
                )
            else:
                ENDOCRINE.pulse(HormoneType.DOPAMINE, +0.05)
        except (AttributeError, sqlite3.Error, asyncio.CancelledError) as e:
            logger.debug("[ORACLE] Audit skipped: %s", e)
        except Exception as e:
            logger.error("[ORACLE] Unexpected audit failure: %s", e)
            raise

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
            # After reset: base_sleep * (1.0 + growth) * r_factor
            # The exponential only kicks in on subsequent clean rounds below.
            derived_sleep = min(base_sleep * (1.0 + growth) * r_factor, self._SLEEP_MAX)
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
        # KAIROS-Ω: Lowered floor for high-adrenaline states
        floor = 0.05 if adrenaline > 0.8 else (0.5 if adrenaline > 0.3 else 1.0)
        return max(floor, final_sleep + _random.uniform(-q_jitter, q_jitter))

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
                            # 🛡️ IMMUNE-SYSTEM-v1: Sovereign Arbiter (Ω₆)
                            # Intercept signal before ignition
                            context = {
                                "reversibility_level": 1,  # Policy actions are R1
                                "confidence_level": 5 if action.value > 0.95 else 4,
                                "is_causal": True,
                                "project": action.project,
                                "action_type": action.action_type,
                            }

                            triage = await self._immune.intercept(action.description, context)

                            if triage.verdict == Verdict.BLOCK:
                                logger.critical(
                                    "🚫 [IMMUNE] Action BLOCKED: %s", action.description
                                )
                                continue
                            elif triage.verdict == Verdict.HOLD:
                                logger.warning(
                                    "⏸️ [IMMUNE] Action HOLD: %s. Justification: %s",
                                    action.description,
                                    triage.risks_assumed[0],
                                )
                                continue

                            logger.warning(
                                "🔥 [APOTHEOSIS] Proactive Healing: %s (Immune PASS: %.1f)",
                                action.description,
                                triage.triage_score,
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

    def _scan_workspace_hashes(
        self, file_hashes: dict[Path, str], hashlib_module: Any
    ) -> list[Path]:
        """Runs the file hashing loop synchronously off the main event loop."""
        files_to_scan = []
        for py_file in self.workspace.rglob("*.py"):
            if _SKIP_DIRS.intersection(py_file.parts):
                continue
            try:
                current_hash = hashlib_module.sha256(py_file.read_bytes()).hexdigest()
                if file_hashes.get(py_file) == current_hash:
                    continue
                file_hashes[py_file] = current_hash
                files_to_scan.append(py_file)
            except OSError:
                continue
        return files_to_scan

    async def _process_workspace(
        self, file_hashes: dict[Path, str], hashlib: Any, _random: Any
    ) -> bool:
        """Scan and heal workspace files (Ω₀/Ω₆) in parallel."""
        entropy_found = False
        try:
            # Delegate blocking filesystem globbing and hashing to bounded thread (Ω₂)
            files_to_scan = await asyncio.to_thread(
                self._scan_workspace_hashes, file_hashes, hashlib
            )

            if files_to_scan:
                # Parallelize entropy scan (Ω₁)
                results = await asyncio.gather(
                    *[asyncio.to_thread(scan_file_entropy, f) for f in files_to_scan],
                    return_exceptions=True,
                )

                for py_file, entropy in zip(files_to_scan, results, strict=False):
                    if isinstance(entropy, list) and entropy:
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
                import ast

                def _parse_ast(name: str, src: str) -> None:
                    ast.parse(src, filename=name)

                source_code = await asyncio.to_thread(py_file.read_text, "utf-8")
                await asyncio.to_thread(_parse_ast, str(py_file), source_code)
                reasons = ", ".join(e["type"] for e in entropy)
                intent = f"Refactor {py_file.name} to eliminate: {reasons}."

                # 🛡️ IMMUNE-SYSTEM-v1: Sovereign Arbiter (Ω₆)
                context = {
                    "reversibility_level": 2,  # Refactoring/Heal is R2
                    "confidence_level": 4,
                    "target_path": str(py_file),
                    "complexity_removed": len(entropy) * 1.0,  # Heuristic
                }

                triage = await self._immune.intercept(intent, context)
                if triage.verdict == Verdict.BLOCK:
                    logger.critical("🚫 [IMMUNE] Healing BLOCKED for %s", py_file.name)
                    return
                elif triage.verdict == Verdict.HOLD:
                    logger.warning("⏸️ [IMMUNE] Healing HOLD for %s", py_file.name)
                    return

                await keter.ignite(intent)
            except SyntaxError:
                logger.error("[APOTHEOSIS] AST Breach: %s. Skipping healing.", py_file.name)
                ENDOCRINE.pulse(HormoneType.ADRENALINE, 0.2, reason="AST Breach detected")
            except (OSError, ValueError, asyncio.CancelledError) as e:
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
