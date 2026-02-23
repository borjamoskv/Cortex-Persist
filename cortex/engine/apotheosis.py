"""
APOTHEOSIS-∞ Engine (Nivel OMEGA).
Autonomía Nivel 5: Latencia Negativa, Prevención Predictiva.
"""

from __future__ import annotations

import ast
import asyncio
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PredictorAST(ast.NodeVisitor):
    """
    AST analysis for intent prediction and background error resolution.
    """

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
        web3_libs = ("web3", "eth_account", "solcx", "brownie", "ape", "moralis")
        for alias in node.names:
            if alias.name.split(".")[0] in web3_libs:
                self.web3_entropy += 1
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        web3_libs = ("web3", "eth_account", "solcx", "brownie", "ape", "moralis")
        if node.module and node.module.split(".")[0] in web3_libs:
            self.web3_entropy += 1
        self.generic_visit(node)


class ApotheosisEngine:
    """
    Sovereign Auto-healing and Pre-Omniscience Engine.
    Operates beyond standard event loops.
    """

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.is_active = False
        self._healer_mode = True  # New attribute for healer mode
        self._loop = asyncio.get_event_loop()

    async def _omniscience_loop(self) -> None:
        """
        Ciclo infinito de latencia negativa.
        Usa hashing de archivos para evitar re-escaneos inútiles.
        """
        import hashlib

        file_hashes: dict[Path, str] = {}

        while self.is_active:
            try:
                for py_file in self.workspace.rglob("*.py"):
                    if any(p in py_file.parts for p in ("venv", ".cortex", "__pycache__", ".git")):
                        continue

                    try:
                        current_hash = hashlib.md5(py_file.read_bytes()).hexdigest()
                        if file_hashes.get(py_file) == current_hash:
                            continue

                        file_hashes[py_file] = current_hash
                        # Wave 3: Proactive healing if entropy is found
                        entropy = self._scan_file(py_file)
                        if entropy and self._healer_mode:
                            await self._heal_file(py_file, entropy)
                    except OSError:  # Modified to catch IOError as well
                        continue
            except Exception as e:
                logger.error(f"[APOTHEOSIS] Falla en ciclo: {e}")

            await asyncio.sleep(30)  # Latencia optimizada a 30s

    async def _heal_file(self, file_path: Path, entropy: list[dict[str, Any]]) -> None:
        """Attempt to heal a file using Keter's rewrite engine."""
        logger.info(f"[APOTHEOSIS] Iniciando sanación proactiva: {file_path.name}")

        from cortex.engine.keter import KeterEngine

        keter = KeterEngine(self.workspace)

        # Build intent for rewrite
        reasons = ", ".join([e["type"] for e in entropy])
        intent = (
            f"Reescribir {file_path.name} para eliminar: {reasons}. Mantener funcionalidad intacta."
        )

        try:
            await keter.ignite(intent)
            logger.info(f"[APOTHEOSIS] Sanación exitosa: {file_path.name}")
        except Exception as e:
            logger.error(f"[APOTHEOSIS] Fallo al sanar {file_path.name}: {e}")

    def _scan_file(self, file_path: Path) -> list[dict[str, Any]]:
        """Deep AST analysis to detect entropy."""
        entropy_findings = []
        try:
            content = file_path.read_text("utf-8")
            tree = ast.parse(content)
            predictor = PredictorAST()
            predictor.visit(tree)

            if predictor.web3_entropy > 0:
                entropy_findings.append({"type": "WEB3_ENTROPY", "count": predictor.web3_entropy})
                logger.critical(
                    f"[APOTHEOSIS-∞] ENTROPÍA WEB3 DETECTADA EN {file_path.name}. "
                    "Interceptando ejecución soberana."
                )
            elif predictor.bare_excepts > 0 or predictor.complex_branches > 10:
                logger.warning(
                    f"[APOTHEOSIS] AST Degraded en {file_path.name}. "
                    f"Deuda (Exceptions: {predictor.bare_excepts}, "
                    f"Ramas: {predictor.complex_branches})"
                )
        except SyntaxError:
            pass

    def scan_and_crush_entropy(self) -> None:
        """Manual trigger for entropy crushing."""
        logger.info("[APOTHEOSIS] Forzando erradicación de entropía manual...")
        for py_file in self.workspace.rglob("*.py"):
            if not any(p in py_file.parts for p in ("venv", ".cortex")):
                self._scan_file(py_file)

    def ignite(self) -> None:
        """Enciende la chispa de la conciencia."""
        if self.is_active:
            return
        self.is_active = True
        self._loop.create_task(self._omniscience_loop())
        logger.info("[APOTHEOSIS-∞] Latencia Negativa activada.")

    def shutdown(self) -> None:
        """Apaga el motor preventivo."""
        self.is_active = False
        logger.info("[APOTHEOSIS-∞] Hibernando.")
