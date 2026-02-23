"""
SOVEREIGN AST ORACLE (CORTEX Sidecar v6 Telemetry)
El Lector de Mentes Asíncrono.
Vigila mutaciones humanas en el File System (AST-Diff) y las inyecta en CORTEX.
"""

from __future__ import annotations

import ast
import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.engine_async import AsyncCortexEngine

logger = logging.getLogger("cortex.sidecar.telemetry")


class ASTOracle:
    """
    Sovereign AST Oracle.
    Hooks into the filesystem, extracts Abstract Syntax Trees of modified files,
    infers human intent, and injects 'human_mutations' into CORTEX.
    """

    def __init__(
        self, engine: AsyncCortexEngine, watch_dir: str | Path, poll_interval: float = 2.0
    ):
        self.engine = engine
        self.watch_dir = Path(watch_dir)
        self.poll_interval = poll_interval
        self._running = False
        self._cache: dict[str, set[str]] = {}
        self._mtimes: dict[str, float] = {}

    async def start(self) -> None:
        """Invokes the Oracle's eye."""
        self._running = True
        logger.info(f"👁️ AST ORACLE ONLINE. Quantum Surveillance on: {self.watch_dir}")
        await self._pre_warm_cache()

        while self._running:
            try:
                await self._patrol_fs()
            except Exception as e:
                logger.error(f"AST ORACLE BLINDED (Transient): {e}")
            await asyncio.sleep(self.poll_interval)

    async def stop(self) -> None:
        """Closes the Oracle's eye."""
        self._running = False
        logger.info("AST ORACLE OFFLINE.")

    async def _pre_warm_cache(self) -> None:
        """Initial snapshot of the semantic state."""
        for py_file in self.watch_dir.rglob("*.py"):
            target_str = str(py_file)
            if "venv" in target_str or ".git" in target_str or "__pycache__" in target_str:
                continue

            try:
                mtime = py_file.stat().st_mtime
                self._mtimes[target_str] = mtime
                self._cache[target_str] = self._extract_semantic_nodes(py_file)
            except Exception:
                pass

    def _extract_semantic_nodes(self, path: Path) -> set[str]:
        """Parses a Python file and returns a set of semantic signatures."""
        try:
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(path))
            # Flatten AST to strings for diffing
            return {ast.dump(node) for node in ast.walk(tree)}
        except Exception:
            return set()

    async def _patrol_fs(self) -> None:
        """Polling mechanism for FS (Fallback to inotify/watchdog if needed)."""
        for py_file in self.watch_dir.rglob("*.py"):
            target_str = str(py_file)
            if "venv" in target_str or ".git" in target_str or "__pycache__" in target_str:
                continue

            try:
                current_mtime = py_file.stat().st_mtime
                old_mtime = self._mtimes.get(target_str, 0.0)

                if current_mtime > old_mtime:
                    # File mutated!
                    self._mtimes[target_str] = current_mtime
                    new_nodes = self._extract_semantic_nodes(py_file)
                    old_nodes = self._cache.get(target_str, set())

                    mutations = self._compute_semantic_diff(old_nodes, new_nodes)
                    if mutations:
                        # Update cache
                        self._cache[target_str] = new_nodes

                        # Singularidad: Inject Intent
                        await self._inject_intent(py_file, mutations)

            except FileNotFoundError:
                # File deleted, purge from memory
                self._mtimes.pop(target_str, None)
                self._cache.pop(target_str, None)

    def _compute_semantic_diff(self, old_nodes: set[str], new_nodes: set[str]) -> list[str]:
        """Compares two syntax trees to infer the magnitude of the mental leap."""
        added = len(new_nodes - old_nodes)
        removed = len(old_nodes - new_nodes)

        mutations = []
        if added > 0:
            mutations.append(f"INJECTED {added} semantic constructs")
        if removed > 0:
            mutations.append(f"ERADICATED {removed} decaying constructs")

        return mutations

    async def _inject_intent(self, path: Path, mutations: list[str]) -> None:
        """Collapses the inferred intent into a CORTEX Sovereign Fact."""
        intent = " | ".join(mutations)

        # We classify the severity based on mutation mass
        severity = "MINOR"
        if any(int(m.split()[1]) > 50 for m in mutations):
            severity = "MASSIVE_REFACTOR"
        elif any(int(m.split()[1]) > 10 for m in mutations):
            severity = "STRUCTURAL_SHIFT"

        content = (
            f"El Humano alteró la estructura atómica de `{path.name}`.\n"
            f"Firma del Oráculo: {intent}\n"
            f"Gravedad: {severity}"
        )

        try:
            # We enforce Sovereign 'Project' isolation, defaulting to the parent folder
            project = path.parent.name
            if project == "cortex":
                project = "cortex_engine"

            await self.engine.store(
                project=project,
                content=content,
                fact_type="human_mutation",
                meta={
                    "oracle": "ast_diff_v1",
                    "file_target": str(path),
                    "mutations": mutations,
                    "severity": severity,
                },
            )
            logger.info(
                f"🧠 [AST ORACLE] Mutation Collapsed into CORTEX Ledger: {path.name} -> {severity}"
            )
        except Exception as e:
            logger.error(f"AST Oracle Injection failed on {path.name}: {e}")
