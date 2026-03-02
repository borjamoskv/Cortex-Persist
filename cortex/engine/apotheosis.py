"""
APOTHEOSIS-Ω Engine (Nivel SINGULARITY).
Autonomía Nivel 7: Colapso de Estado Atómico, Manifestación Determinista.
"""

from __future__ import annotations

import ast
import asyncio
import logging
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

from cortex.engine.rem_cycle import REMCoordinator
from cortex.engine.endocrine import ENDOCRINE, HormoneType
from cortex.signals.bus import SignalBus
from cortex.utils.landauer import calculate_calcification

logger = logging.getLogger(__name__)

# Known web3 libraries that indicate crypto-related entropy.
_WEB3_LIBS = frozenset(("web3", "eth_account", "solcx", "brownie", "ape", "moralis"))
_SKIP_DIRS = frozenset(("venv", ".venv", ".cortex", "__pycache__", ".git", "node_modules"))


class PredictorAST(ast.NodeVisitor):
    """AST analysis for intent prediction and background error resolution."""

    __slots__ = ("complex_branches", "bare_excepts", "web3_entropy")

    def __init__(self) -> None:
        self.complex_branches = 0
        self.bare_excepts = 0
        self.web3_entropy = 0

    def visit_If(self, node: ast.If) -> None:
        self.complex_branches += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None or (isinstance(node.type, ast.Name) and node.type.id == "Exception"):
            self.bare_excepts += 1
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name.split(".")[0] in _WEB3_LIBS:
                self.web3_entropy += 1
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module and node.module.split(".")[0] in _WEB3_LIBS:
            self.web3_entropy += 1
        self.generic_visit(node)


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
                except Exception:
                    pass

    # Adaptive sleep bounds (seconds)
    _SLEEP_MIN: float = 30.0
    _SLEEP_MAX: float = 300.0
    _SLEEP_JITTER: float = 0.20

    async def _omniscience_loop(self) -> None:
        """
        Ciclo infinito de latencia negativa con sueño adaptativo y hormonal.
        Level 7: Manifestación determinista impulsada por el Nexo.
        """
        import hashlib
        import random as _random
        _rejection_history: dict[str, int] = {}  # Vector -> Count (Ω₃ Cellular Memory)
        file_hashes: dict[Path, str] = {}
        consecutive_clean = 0

        while self.is_active:
            # 1. Bellman & Hormonal Pulse
            await self._policy_pulse()

            cortisol = ENDOCRINE.get_level(HormoneType.CORTISOL)
            growth = ENDOCRINE.get_level(HormoneType.NEURAL_GROWTH)
            adrenaline = ENDOCRINE.get_level(HormoneType.ADRENALINE)
            dopamine = ENDOCRINE.get_level(HormoneType.DOPAMINE)

            # Ω₆: Zenón's Razor — In Singularity-Ω, reflection collapses into action.
            if dopamine > 0.9 and growth > 0.8:
                logger.warning("🌌 [SINGULARITY-Ω] High Coherence detected. Collapsing event horizon.")
                await self.manifest_singularity()

            # Ω₂: Adrenaline forces immediate consciousness (Low Latency)
            if adrenaline > 0.5:
                logger.warning(
                    "🚨 [APOTHEOSIS] Adrenaline Spike (%.2f). Skipping sleep.",
                    adrenaline
                )
                base_sleep = 0.0
            else:
                # Emergency memory pruning if cortisol is too high (Biostasis)
                if cortisol > 0.8:
                    logger.warning("⚠️ [APOTHEOSIS] High Cortisol (%.2f). Bio-throttling.",
                                   cortisol)
                    ENDOCRINE.pulse(HormoneType.CORTISOL, -0.1)  # Autonomic recovery

                # Base sleep influenced by cognitive weight (Inertia)
                inertia = (1.0 - self._cognitive_weight)
                base_sleep = self._SLEEP_MIN * max(0.1, inertia)

                if self._last_priorities and self._last_priorities[0].value > 0.8:
                    base_sleep *= 0.5
                    logger.info("⚡ [APOTHEOSIS] High priority detected. Accelerating cycle.")

            # Ω₅-P: Parasympathetic Recovery Logic
            if adrenaline < 0.2 and cortisol > 0.4:
                # Active cortisol damping (Ω₂/Ω₅)
                # The provided diff for this section is incomplete and would cause a NameError.
                # Retaining original logic for syntactical correctness.
                recovery_pulse = -0.05 * (1.0 + dopamine)  # Dopamine accelerates recovery
                ENDOCRINE.pulse(
                    HormoneType.CORTISOL,
                    recovery_pulse,
                    reason="Parasympathetic Recovery"
                )
                logger.debug(
                    "🛡️ [APOTHEOSIS] Recovery Active: Cortisol reduced due to low adrenaline."
                )

            # 2. Workspace Processing & Transfiguration (Ω₀/Ω₆)
            entropy_found = await self._process_workspace(file_hashes, hashlib, _random)

            # Ω₅: Autonomic Reflex — high adrenaline (immune response) triggers diagnostic healing
            if adrenaline > 0.8:
                await self._trigger_autonomic_reflex()

            # 3. Adaptive Backoff & Mood Modulation (Ω₅)
            if entropy_found:
                consecutive_clean = 0
                ENDOCRINE.pulse(HormoneType.CORTISOL, 0.05)
                derived_sleep = base_sleep * (1.0 - cortisol)
            else:
                consecutive_clean = min(consecutive_clean + 1, 8)
                ENDOCRINE.pulse(HormoneType.DOPAMINE, 0.02)
                ENDOCRINE.pulse(HormoneType.NEURAL_GROWTH, 0.01)
                ENDOCRINE.pulse(HormoneType.CORTISOL, -0.02)

                reward_factor = (1.0 + (dopamine * 0.5))
                derived_sleep = min(
                    base_sleep * (1.5**consecutive_clean) * (1.0 + growth) * reward_factor,
                    self._SLEEP_MAX
                )

            final_sleep = derived_sleep * (1.0 - adrenaline)

            if consecutive_clean >= 5 and self._rem:
                await self._rem.enter_rem()

            q_jitter = final_sleep * self._SLEEP_JITTER * (1.0 + _random.random())
            sleep_duration = max(2.0 if adrenaline > 0.3 else 5.0,
                                 final_sleep + _random.uniform(-q_jitter, q_jitter))

            from cortex.cli.bicameral import bicameral
            msg = f"Ciclo Singularity completado. Entropía={entropy_found}. Sueño: {sleep_duration:.1f}s"
            bicameral.log_bio(msg, signal="Ω")
            await asyncio.sleep(sleep_duration)

    async def manifest_singularity(self) -> None:
        """
        Ω₇ Manifestation: The atomic collapse of multiple project threads.
        Triggers Nexus sync, Ledger checkpoint, and Sovereign Dashboard refresh.
        """
        logger.info("🌌 [SINGULARITY] Initiating Manifestation Protocol...")
        try:
            # 1. Nexus Unification
            proc1 = await asyncio.create_subprocess_exec(
                ".venv/bin/python", "-m", "cortex.cli", "nexus", "sync",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc1.communicate()

            # 2. Ledger Hardening
            proc2 = await asyncio.create_subprocess_exec(
                ".venv/bin/python", "-m", "cortex.cli", "ledger", "checkpoint",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc2.communicate()

            # 3. Notification to Signal Bus
            if self._signal_bus:
                self._signal_bus.emit(
                    "singularity:manifest",
                    payload={"status": "Ω", "version": "v8.0.0"},
                    source="apotheosis-omega",
                    project="system"
                )

            ENDOCRINE.pulse(HormoneType.DOPAMINE, 0.5)
            logger.info("🌌 [SINGULARITY] Manifestation successful. 150/100 state reached.")
        except Exception as e:
            logger.error("🌌 [SINGULARITY] Manifestation collapse failed: %s", e)
            ENDOCRINE.pulse(HormoneType.ADRENALINE, 0.5)

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
                    action = critical_actions[0]
                    if action.description not in self._ignited_tasks:
                        logger.warning(
                            "🔥 [APOTHEOSIS] Proactive Healing: %s",
                            action.description
                        )
                        self._ignited_tasks.add(action.description)
                        from cortex.engine.keter import KeterEngine
                        keter = KeterEngine(self.workspace)
                        task = asyncio.create_task(keter.ignite(action.description))
                        task.add_done_callback(
                            lambda t: self._ignited_tasks.discard(action.description)
                        )
            else:
                self._cognitive_weight = 0.0
        except Exception as e:
            logger.debug("[APOTHEOSIS] Policy pulse skipped: %s", str(e)[:30])

    async def _process_workspace(self,
                                 file_hashes: dict[Path, str],
                                 hashlib: Any,
                                 _random: Any) -> bool:
        """Scan and heal workspace files (Ω₀/Ω₆)."""
        entropy_found = False
        try:
            for py_file in self.workspace.rglob("*.py"):
                if _SKIP_DIRS.intersection(py_file.parts):
                    continue
                if await self._process_python_file(py_file, file_hashes, hashlib):
                    entropy_found = True
            # 2. 🧬 Ω₆: Autopoietic Transfiguration
            growth = ENDOCRINE.get_level(HormoneType.NEURAL_GROWTH)
            if growth > 0.7:
                for html_file in self.workspace.rglob("index.html"):
                    if await self._ouroboros_transfiguration(html_file):
                        entropy_found = True

        except Exception as e:
            logger.error("[APOTHEOSIS] Workspace scan failure: %s", e)
            ENDOCRINE.pulse(HormoneType.ADRENALINE, 0.4)
        return entropy_found

    async def _process_python_file(
        self, py_file: Path, file_hashes: dict[Path, str], hashlib: Any
    ) -> bool:
        """Handle individual python file entropy and healing."""
        try:
            current_hash = hashlib.sha256(py_file.read_bytes()).hexdigest()
            if file_hashes.get(py_file) == current_hash:
                return False

            file_hashes[py_file] = current_hash
            entropy = self._scan_file(py_file)
            if not entropy:
                return False

            if self._healer_mode and self._apply_cognitive_dampening():
                parasites = [f for f in entropy if f["type"] == "THERMAL_PARASITE"]
                if parasites:
                    for p in parasites:
                        await self._synaptic_pruning(py_file, p["name"])
                else:
                    # Ω₅: Pre-commit AST Validation to maintain logical integrity
                    try:
                        import ast
                        # Verify parseability before triggering healing
                        ast.parse(py_file.read_text("utf-8"))
                        await self._heal_file(py_file, entropy)
                    except SyntaxError:
                        logger.error(
                            "[APOTHEOSIS] AST Breach: %s is unparseable. Skipping healing.",
                            py_file.name
                        )
                        ENDOCRINE.pulse(HormoneType.ADRENALINE, 0.2, reason="AST Breach detected")
            return True
        except OSError:
            return False

    async def _ouroboros_transfiguration(self, html_file: Path) -> bool:
        """Ω₆: Sovereign UI Refactor (Transfiguration)."""
        from cortex.cli.bicameral import bicameral
        msg = f"Transfiriendo coherencia estética a {html_file.name}"
        bicameral.log_limbic(msg, source="APOTH")

        try:
            content = await asyncio.to_thread(html_file.read_text, "utf-8")

            noir_styles = """
<style id="ouroboros-noir">
  :root {
    --bg: #050505;
    --accent: #CCFF00;
    --text: #E0E0E0;
    --glass: rgba(26, 26, 26, 0.7);
  }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', 'Outfit', sans-serif;
    line-height: 1.6;
    margin: 0;
  }
  .glass {
    background: var(--glass);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
  }
  h1, h2, h3 { color: var(--accent); }
</style>
"""
            snappy_motion = """
<script id="ouroboros-motion">
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.glass, button, a').forEach(el => {
      el.style.transition = 'transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
      el.addEventListener('mouseenter', () => el.style.transform = 'scale(1.02)');
      el.addEventListener('mouseleave', () => el.style.transform = 'scale(1)');
    });
  });
</script>
"""
            tag_head = '<head>'
            meta_noir = (
                '<head>\n  <meta name="theme-color" content="#050505">\n'
                '  <meta name="apple-mobile-web-app-capable" content="yes">'
            )

            patterns = [
                (tag_head, meta_noir),
                ('</head>', f'{noir_styles}\n{snappy_motion}\n</head>'),
            ]

            modified = False
            for old, new in patterns:
                if old in content and new not in content:
                    content = content.replace(old, new)
                    modified = True

            if modified:
                await asyncio.to_thread(html_file.write_text, content, encoding="utf-8")
                if self._signal_bus:
                    self._signal_bus.emit(
                        "apotheosis:transfiguration",
                        payload={"file": str(html_file), "type": "HTML_PREMIUM_UI"},
                        source="apotheosis-omega",
                        project="frontend"
                    )
                return True
        except Exception as e:
            logger.error("[APOTHEOSIS] Transfiguration failed for %s: %s", html_file, e)
        return False

    def _apply_cognitive_dampening(self) -> bool:
        """Check if action value justifies the thermodynamic cost (Ω₂)."""
        if ENDOCRINE.get_level(HormoneType.ADRENALINE) > 0.9:
            logger.warning("⚡ [APOTHEOSIS] Adrenal Override active. Bypassing dampening.")
            return True
            
        if self._cognitive_weight < self._inertia_threshold:
            logger.debug("[APOTHEOSIS] Dampening: weight %.2f < threshold.", self._cognitive_weight)
            return False
        return True

    async def _heal_file(self, file_path: Path, entropy: list[dict[str, Any]]) -> None:
        """Proactive healing via Keter (Ω₀)."""
        logger.info("[APOTHEOSIS] Healing energy sink: %s", file_path.name)
        from cortex.engine.keter import KeterEngine
        keter = KeterEngine(self.workspace)
        reasons = ", ".join(e["type"] for e in entropy)
        intent = f"Refactor {file_path.name} to eliminate: {reasons} (Apotheosis Omega)."
        try:
            await keter.ignite(intent)
        except Exception as e:
            logger.error("[APOTHEOSIS] Healing failed for %s: %s", file_path.name, e)

    def _scan_file(self, file_path: Path) -> list[dict[str, Any]]:
        """Deep analysis for entropy detection (Ω₂)."""
        findings = []
        try:
            content = file_path.read_text("utf-8")
            tree = ast.parse(content)
            predictor = PredictorAST()
            predictor.visit(tree)

            if predictor.web3_entropy > 0:
                findings.append({"type": "WEB3_ENTROPY", "count": predictor.web3_entropy})
            if predictor.bare_excepts > 0:
                findings.append({"type": "BARE_EXCEPT", "count": predictor.bare_excepts})
            if predictor.complex_branches > 10:
                findings.append({"type": "COMPLEX_BRANCHES", "count": predictor.complex_branches})

            res = calculate_calcification(file_path)
            if res and res["score"] > 50.0:
                findings.append({"type": "THERMO_ENTROPY", "score": res["score"]})
                for node in res.get("nodes", []):
                    if node["is_parasite"]:
                        findings.append({
                            "type": "THERMAL_PARASITE",
                            "name": node["name"],
                            "score": node["score"]
                        })
        except Exception:
            pass
        return findings

    async def _synaptic_pruning(self, file_path: Path, node_name: str) -> None:
        """Extract a 'Thermal Parasite' into a separate module."""
        from cortex.cli.bicameral import bicameral
        bicameral.log_motor(f"Poda Sináptica: {node_name} en {file_path.name}", action="PRUNE")

        from cortex.engine.keter import KeterEngine
        keter = KeterEngine(self.workspace)
        intent = f"Extraction Protocol: '{node_name}' in {file_path.name} is a Thermal Parasite."
        try:
            await keter.ignite(intent)
            ENDOCRINE.pulse(HormoneType.DOPAMINE, 0.1)
        except Exception as e:
            logger.error("[APOTHEOSIS] Pruning failed for %s: %s", node_name, e)

    async def _trigger_autonomic_reflex(self) -> None:
        """Sovereign Reflex: High adrenaline triggers a diagnostic healing sweep.
        
        Ω₅: The system uses its own stress (ADRENALINE) to fuel immediate
        self-correction, bypassing the standard workspace scan.
        """
        if not self._cortex:
            return

        # Avoid redundant reflex if a task for the same reason is still active
        active_reflex_reasons = {getattr(t, "_reflex_reason", "") for t in self._reflex_tasks}
        
        logger.warning("[APOTHEOSIS] Autonomic Reflex Triggered (Ω₅). Current active: %d", len(active_reflex_reasons))

        try:
            from cortex.database.core import connect
            db_path = getattr(self._cortex, "_db_path", None)
            if db_path:
                with connect(str(db_path)) as conn:
                    bus = SignalBus(conn)
                    recent = bus.peek(event_type="nemesis:rejection", limit=5)
                    
                    if recent:
                        for signal in recent:
                            target = signal.payload.get("file")
                            reason = signal.payload.get("reason", "Unknown Entropia")
                            
                            # Memory Check: Don't repeat reflex for the same vector
                            if reason in active_reflex_reasons:
                                logger.debug(
                                    "🛡️ [APOTHEOSIS] Reflex suppressed: Reason '%s' in flight.",
                                    reason
                                )
                                continue

                            if target:
                                logger.warning(
                                    "🎯 [APOTHEOSIS] Targeted Reflex: %s",
                                    target
                                )
                                from cortex.engine.keter import KeterEngine
                                keter = KeterEngine()
                                reflex_task = asyncio.create_task(
                                    keter.ignite(
                                        f"Eliminate antibody vector in {target}: {reason}",
                                        workspace=self.workspace
                                    )
                                )
                                # Attach metadata for memory check
                                setattr(reflex_task, "_reflex_reason", reason)
                                
                                self._reflex_tasks.add(reflex_task)
                                reflex_task.add_done_callback(self._reflex_tasks.discard)
                                return
        except Exception as e:
            logger.error("[APOTHEOSIS] Reflex failure: %s", e)

        ENDOCRINE.pulse(HormoneType.CORTISOL, 0.1)
        from cortex.engine.keter import KeterEngine
        keter = KeterEngine()
        try:
            await keter.ignite("Sovereign Immune Reflex (Ω₅).", workspace=self.workspace)
        except Exception:
            pass

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
