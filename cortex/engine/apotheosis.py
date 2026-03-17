"""APOTHEOSIS-Ω Engine: Sovereign Singularity & Manifestation (Level 7)."""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from watchdog.events import FileSystemEvent as FileSystemEvent
    from watchdog.events import FileSystemEventHandler as FileSystemEventHandler
    from watchdog.observers import Observer as Observer

    from cortex.engine import CortexEngine

    _HAS_WATCHDOG = True
else:
    try:
        from watchdog.events import FileSystemEvent, FileSystemEventHandler
        from watchdog.observers import Observer

        _HAS_WATCHDOG = True
    except ImportError:
        _HAS_WATCHDOG = False

        class FileSystemEventHandler:  # type: ignore
            pass

        class FileSystemEvent:  # type: ignore
            pass

        class Observer:  # type: ignore
            pass


from cortex.engine.apotheosis_audits_mixin import ApotheosisAuditsMixin
from cortex.engine.cognitive import scan_file_entropy
from cortex.engine.endocrine import ENDOCRINE, HormoneType
from cortex.engine.manifestation import transfigure_ui
from cortex.engine.reflex import trigger_autonomic_reflex
from cortex.engine.rem_cycle import REMCoordinator
from cortex.extensions.immune.membrane import ImmuneMembrane, Verdict
from cortex.extensions.signals.bus import SignalBus
from cortex.services.notebooklm import NotebookLMService
from cortex.services.trust import TrustService

logger = logging.getLogger(__name__)

_SKIP_DIRS = frozenset(("venv", ".venv", ".cortex", "__pycache__", ".git", "node_modules"))


class _WorkspaceEventHandler(FileSystemEventHandler):
    """(Ω₂) Captures physical OS events instead of thermal-heavy rglob polling."""

    def __init__(self, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue[Path]) -> None:
        self.loop = loop
        self.queue = queue

    def _enqueue(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        src_path = event.src_path
        if isinstance(src_path, bytes):
            src_path = src_path.decode("utf-8")
        if not src_path.endswith(".py"):
            return
        path = Path(src_path)
        if not _SKIP_DIRS.intersection(path.parts):
            self.loop.call_soon_threadsafe(self.queue.put_nowait, path)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._enqueue(event)

    def on_created(self, event: FileSystemEvent) -> None:
        self._enqueue(event)


class ApotheosisEngine(ApotheosisAuditsMixin):
    """Sovereign Singularity & Manifestation Engine (Level 7)."""

    def __init__(
        self,
        workspace: Path,
        cortex_engine: Optional[CortexEngine] = None,
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
        self._immune = ImmuneMembrane(engine=cortex_engine)
        self._file_event_queue: Optional[asyncio.Queue[Path]] = None
        self._observer: Any = None

        if cortex_engine:
            db_path = str(getattr(cortex_engine, "_db_path", ""))
            if db_path:
                self._trust = TrustService(db_path)
                self._notebooklm = NotebookLMService(db_path)
            db = getattr(cortex_engine, "db", None)
            if db:
                self._rem = REMCoordinator(db)
                try:
                    sync_conn = getattr(db, "_conn", db)
                    if isinstance(sync_conn, sqlite3.Connection):
                        self._signal_bus = SignalBus(sync_conn)
                        self._signal_bus.ensure_table()
                except (sqlite3.OperationalError, OSError, AttributeError) as err:
                    logger.debug("[APOTHEOSIS] SignalBus init skipped: %s", err)

    def _spawn_reflex(self, coro: Any) -> asyncio.Task[Any]:
        """Create a background reflex task with auto-cleanup."""
        task = asyncio.create_task(coro)
        self._reflex_tasks.add(task)
        task.add_done_callback(self._reflex_tasks.discard)
        return task

    _SLEEP_MIN: float = 0.1
    _SLEEP_MAX: float = 60.0
    _SLEEP_JITTER: float = 0.05

    async def _omniscience_loop(self) -> None:
        """Ciclo infinito de latencia negativa con sueño adaptativo y hormonal."""
        import random as _random

        consecutive_clean = 0

        while self.is_active:
            await self._policy_pulse()
            cortisol = ENDOCRINE.get_level(HormoneType.CORTISOL)
            growth = ENDOCRINE.get_level(HormoneType.NEURAL_GROWTH)
            adrenaline = ENDOCRINE.get_level(HormoneType.ADRENALINE)
            dopamine = ENDOCRINE.get_level(HormoneType.DOPAMINE)

            await self._check_singularity_state(dopamine, growth)

            base_sleep = self._apply_hormonal_shifts(adrenaline, cortisol, dopamine)

            entropy_found = await self._process_workspace(_random)

            if adrenaline > 0.8:
                await trigger_autonomic_reflex(self.workspace, self._cortex, self._reflex_tasks)

            consecutive_clean, derived_sleep = self._calc_recovery(
                entropy_found, consecutive_clean, base_sleep, growth, dopamine, cortisol
            )

            if consecutive_clean >= 5 and self._rem:
                await self._rem.enter_rem()
                self._spawn_reflex(self._oracle_audit())
                self._spawn_reflex(self._sync_notebooklm())
                self._spawn_reflex(self._metamemory_audit())

            duration = self._calc_duration(derived_sleep, adrenaline, _random)

            from cortex.cli.bicameral import bicameral

            bicameral.log_bio(
                f"Ciclo Ω. Entropía={entropy_found}. Sueño: {duration:.1f}s", signal="Ω"
            )
            # Bypass sleep during high-adrenaline state
            if adrenaline > 0.8:
                bicameral.log_bio("Adrenal Overdrive: Bypassing sleep.", signal="⚡")
                continue

            if duration > 0.01:
                await asyncio.sleep(duration)

    async def _policy_pulse(self) -> None:
        """Fetch priorities from PolicyEngine (Ω₃)."""
        if not self._cortex:
            return
        try:
            from cortex.extensions.policy import PolicyConfig, PolicyEngine

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
                            task = self._spawn_reflex(keter.ignite(action.description))
                            task.add_done_callback(
                                lambda t, a=action: self._ignited_tasks.discard(a.description)
                            )
            else:
                self._cognitive_weight = 0.0
        except (ImportError, RuntimeError, sqlite3.Error, AttributeError) as e:
            logger.debug("[APOTHEOSIS] Policy pulse skipped: %s", str(e)[:30])

    async def _process_workspace(self, _random: Any) -> bool:
        """Scan and heal workspace files (Ω₀/Ω₆) mapped from physical OS events."""
        entropy_found = False
        try:
            # Consume filesystem events
            if self._file_event_queue is None:
                return False

            files_to_scan: set[Path] = set()
            while not self._file_event_queue.empty():
                try:
                    files_to_scan.add(self._file_event_queue.get_nowait())
                except asyncio.QueueEmpty:
                    break

            if files_to_scan:
                scan_tasks = [asyncio.to_thread(scan_file_entropy, f) for f in files_to_scan]
                results = await asyncio.gather(*scan_tasks, return_exceptions=True)

                scan_files_list = list(files_to_scan)

                for py_file, entropy in zip(scan_files_list, results, strict=True):
                    if isinstance(entropy, list) and entropy:
                        entropy_found = True
                        if self._healer_mode and self._apply_cognitive_dampening():
                            await self._heal_file_or_prune(py_file, entropy)

            # Autopoietic Transfiguration
            growth = ENDOCRINE.get_level(HormoneType.NEURAL_GROWTH)
            if growth > 0.7:
                for html_file in self.workspace.rglob("index.html"):
                    if await transfigure_ui(html_file, self._signal_bus):
                        entropy_found = True

        except (OSError, asyncio.CancelledError, RuntimeError) as e:
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
                except (RuntimeError, AttributeError, OSError) as e:
                    logger.error("[APOTHEOSIS] Pruning failed for %s: %s", node_name, e)
        else:
            try:
                import ast

                def _parse_ast(name: str, src: str) -> None:
                    ast.parse(src, filename=name)

                source_code = await asyncio.to_thread(py_file.read_text, "utf-8")
                await asyncio.to_thread(_parse_ast, str(py_file), source_code)
                reasons = ", ".join(e["type"] for e in entropy)
                intent = f"Refactor {py_file.name} to eliminate: {reasons}."

                context = {
                    "reversibility_level": 2,
                    "confidence_level": 4,
                    "target_path": str(py_file),
                    "complexity_removed": len(entropy) * 1.0,
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

    def ignite(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """Ignite the Apotheosis consciousness with kernel-level filesystem hooks."""
        if self.is_active:
            return
        self.is_active = True
        _loop = loop or asyncio.get_running_loop()

        # Mount Event Horizon Watcher
        self._file_event_queue = asyncio.Queue()
        event_handler = _WorkspaceEventHandler(_loop, self._file_event_queue)

        if _HAS_WATCHDOG:
            self._observer = Observer()
            if self._observer:
                self._observer.schedule(event_handler, str(self.workspace), recursive=True)
                self._observer.start()

        _loop.create_task(self._omniscience_loop())
        logger.info("[APOTHEOSIS-Ω] Latencia Negativa (Ω₇) — OS Hooks Mounted.")

    def shutdown(self) -> None:
        """Hibernation protocol and filesystem detachment."""
        self.is_active = False
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
        logger.info("[APOTHEOSIS-Ω] Hibernando.")
