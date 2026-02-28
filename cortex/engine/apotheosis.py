"""
APOTHEOSIS-∞ Engine (Nivel OMEGA).
Autonomía Nivel 5: Latencia Negativa, Prevención Predictiva.
"""

from __future__ import annotations

import ast
import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

logger = logging.getLogger(__name__)


# Known web3 libraries that indicate crypto-related entropy.
_WEB3_LIBS = frozenset(("web3", "eth_account", "solcx", "brownie", "ape", "moralis"))


class PredictorAST(ast.NodeVisitor):
    """AST analysis for intent prediction and background error resolution."""

    __slots__ = (
        "technical_debt_score",
        "complex_branches",
        "bare_excepts",
        "web3_entropy",
    )

    def __init__(self) -> None:
        self.technical_debt_score = 0
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


# Directories to skip during workspace scanning.
_SKIP_DIRS = frozenset(("venv", ".venv", ".cortex", "__pycache__", ".git", "node_modules"))


class ApotheosisEngine:
    """Sovereign Auto-healing and Pre-Omniscience Engine."""

    def __init__(
        self,
        workspace: Path,
        cortex_engine: CortexEngine | None = None,
    ) -> None:
        self.workspace = workspace
        self.is_active = False
        self._healer_mode = True
        self._cortex = cortex_engine  # Bellman Policy Engine integration
        self._last_priorities: list = []  # Cached policy results

    # Adaptive sleep bounds (seconds)
    _SLEEP_MIN: float = 30.0  # active / entropy found
    _SLEEP_MAX: float = 300.0  # quiescent / everything clean
    _SLEEP_JITTER: float = 0.20  # ±20% to prevent thundering herd

    async def _omniscience_loop(self) -> None:
        """
        Ciclo infinito de latencia negativa con sueño adaptativo.

        - Usa hashing de archivos para evitar re-escaneos inútiles.
        - Duerme más tiempo cuando el workspace está limpio (backoff).
        - Duerme menos cuando detecta entropía activa (respuesta rápida).
        - Aplica jitter ±20% para evitar thundering herd en swarm.
        """
        import hashlib
        import random as _random

        file_hashes: dict[Path, str] = {}
        consecutive_clean = 0  # tracks quiescent cycles for backoff

        while self.is_active:
            # Bellman pulse: surface top priorities from CORTEX memory.
            await self._policy_pulse()

            entropy_found = await self._process_workspace(
                file_hashes,
                hashlib,
                _random,
            )

            # Adaptive backoff: longer sleep when clean, shorter when busy
            if entropy_found:
                consecutive_clean = 0
                base_sleep = self._SLEEP_MIN
            else:
                consecutive_clean = min(consecutive_clean + 1, 8)
                base_sleep = min(
                    self._SLEEP_MIN * (1.5**consecutive_clean),
                    self._SLEEP_MAX,
                )

            jitter = base_sleep * self._SLEEP_JITTER
            sleep_duration = base_sleep + _random.uniform(-jitter, jitter)
            logger.debug(
                "[APOTHEOSIS] Ciclo completado. Entropía=%s. Durmiendo %.1fs",
                entropy_found,
                sleep_duration,
            )
            await asyncio.sleep(sleep_duration)

    # ── Bellman Policy Pulse ───────────────────────────────────────

    async def _policy_pulse(self) -> None:
        """Query the PolicyEngine for top Bellman-scored priorities.

        Runs non-destructively alongside entropy scanning to surface
        WHAT matters most from CORTEX memory (ghosts, errors, bridges).
        """
        if not self._cortex:
            return
        try:
            from cortex.policy import PolicyConfig, PolicyEngine

            config = PolicyConfig(max_actions=5)
            policy = PolicyEngine(self._cortex, config)
            actions = await policy.evaluate()
            self._last_priorities = actions

            if actions:
                top = actions[0]
                logger.info(
                    "[APOTHEOSIS] 🎯 Policy pulse: %d priorities. "
                    "Top: V=%.3f [%s] %s",
                    len(actions),
                    top.value,
                    top.action_type,
                    top.description[:80],
                )
        except Exception as e:
            logger.debug("[APOTHEOSIS] Policy pulse skipped: %s", e)

    async def _process_workspace(
        self,
        file_hashes: dict[Path, str],
        hashlib: Any,
        _random: Any,
    ) -> bool:
        """Scan workspace for entropy. Returns True if entropy was found."""
        entropy_found = False
        try:
            for py_file in self.workspace.rglob("*.py"):
                if _SKIP_DIRS.intersection(py_file.parts):
                    continue
                try:
                    current_hash = hashlib.md5(
                        py_file.read_bytes(),
                    ).hexdigest()
                    if file_hashes.get(py_file) == current_hash:
                        continue
                    file_hashes[py_file] = current_hash
                    entropy = self._scan_file(py_file)
                    if entropy:
                        entropy_found = True
                        if self._healer_mode:
                            await self._heal_file(py_file, entropy)
                except OSError:
                    continue
        except (OSError, RuntimeError) as e:
            logger.error("[APOTHEOSIS] Falla en ciclo: %s", e)
        return entropy_found

    async def _heal_file(
        self,
        file_path: Path,
        entropy: list[dict[str, Any]],
    ) -> None:
        """Attempt to heal a file using Keter's rewrite engine."""
        logger.info("[APOTHEOSIS] Iniciando sanación proactiva: %s", file_path.name)

        from cortex.engine.keter import KeterEngine

        keter = KeterEngine(self.workspace)
        reasons = ", ".join(e["type"] for e in entropy)
        intent = (
            f"Reescribir {file_path.name} para eliminar: {reasons}. Mantener funcionalidad intacta."
        )

        try:
            await keter.ignite(intent)
            logger.info("[APOTHEOSIS] Sanación exitosa: %s", file_path.name)
        except (OSError, RuntimeError, ValueError) as e:
            logger.error("[APOTHEOSIS] Fallo al sanar %s: %s", file_path.name, e)

    def _scan_file(self, file_path: Path) -> list[dict[str, Any]]:
        """Deep AST analysis to detect entropy."""
        entropy_findings: list[dict[str, Any]] = []
        try:
            content = file_path.read_text("utf-8")
            tree = ast.parse(content)
            predictor = PredictorAST()
            predictor.visit(tree)

            if predictor.web3_entropy > 0:
                entropy_findings.append(
                    {"type": "WEB3_ENTROPY", "count": predictor.web3_entropy},
                )
                logger.critical(
                    "[APOTHEOSIS-∞] ENTROPÍA WEB3 DETECTADA EN %s. "
                    "Interceptando ejecución soberana.",
                    file_path.name,
                )
            if predictor.bare_excepts > 0:
                entropy_findings.append(
                    {"type": "BARE_EXCEPT", "count": predictor.bare_excepts},
                )
            if predictor.complex_branches > 10:
                entropy_findings.append(
                    {"type": "COMPLEX_BRANCHES", "count": predictor.complex_branches},
                )
            if predictor.bare_excepts > 0 or predictor.complex_branches > 10:
                logger.warning(
                    "[APOTHEOSIS] AST Degraded en %s. Deuda (Exceptions: %d, Ramas: %d)",
                    file_path.name,
                    predictor.bare_excepts,
                    predictor.complex_branches,
                )
        except SyntaxError:
            pass
        return entropy_findings

    def scan_and_crush_entropy(self) -> list[dict[str, Any]]:
        """Manual trigger for entropy crushing. Returns all findings."""
        logger.info("[APOTHEOSIS] Forzando erradicación de entropía manual...")
        all_findings: list[dict[str, Any]] = []
        for py_file in self.workspace.rglob("*.py"):
            if not _SKIP_DIRS.intersection(py_file.parts):
                all_findings.extend(self._scan_file(py_file))
        return all_findings

    def ignite(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        """Enciende la chispa de la conciencia."""
        if self.is_active:
            return
        self.is_active = True
        _loop = loop or asyncio.get_running_loop()
        _loop.create_task(self._omniscience_loop())
        logger.info("[APOTHEOSIS-∞] Latencia Negativa activada.")

    def shutdown(self) -> None:
        """Apaga el motor preventivo."""
        self.is_active = False
        logger.info("[APOTHEOSIS-∞] Hibernando.")
