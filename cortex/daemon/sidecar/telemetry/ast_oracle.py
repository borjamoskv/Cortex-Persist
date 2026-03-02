"""SOVEREIGN AST ORACLE (CORTEX Sidecar v6 Telemetry)
El Lector de Mentes Asíncrono.

Sovereign 200: Uses watchdog filesystem events instead of polling rglob.
Detects human mutations at the OS kernel level (kqueue/inotify)
and injects them into CORTEX — O(1) per event instead of O(N) per tick.
"""

from __future__ import annotations

import ast
import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

if TYPE_CHECKING:
    from cortex.engine_async import AsyncCortexEngine

logger = logging.getLogger("cortex.sidecar.telemetry")

_SKIP_DIRS = frozenset(("venv", ".venv", ".git", "__pycache__", "node_modules"))


class _ASTEventHandler(FileSystemEventHandler):
    """(Ω₂) Captures Python file mutations via OS-level events."""

    def __init__(self, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue[Path]) -> None:
        self.loop = loop
        self.queue = queue

    def _enqueue(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        src = event.src_path
        if isinstance(src, bytes):
            src = src.decode("utf-8")
        if not src.endswith(".py"):
            return
        path = Path(src)
        if not _SKIP_DIRS.intersection(path.parts):
            self.loop.call_soon_threadsafe(self.queue.put_nowait, path)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._enqueue(event)

    def on_created(self, event: FileSystemEvent) -> None:
        self._enqueue(event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        self._enqueue(event)


class ASTOracle:
    """Sovereign AST Oracle.

    Hooks into the filesystem via kernel-level events (watchdog),
    extracts Abstract Syntax Trees of modified files,
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
        self._event_queue: asyncio.Queue[Path] | None = None
        self._observer: Observer | None = None

    async def start(self) -> None:
        """Invokes the Oracle's eye with kernel-level filesystem hooks."""
        self._running = True
        logger.info("👁️ AST ORACLE ONLINE. Sovereign Surveillance on: %s", self.watch_dir)

        # Pre-warm cache from existing files (one-time O(N) bootstrap)
        await self._pre_warm_cache()

        # Mount watchdog observer for O(1) event-driven detection
        loop = asyncio.get_running_loop()
        self._event_queue = asyncio.Queue()
        handler = _ASTEventHandler(loop, self._event_queue)
        self._observer = Observer()
        if self._observer:
            self._observer.schedule(handler, str(self.watch_dir), recursive=True)
            self._observer.start()

        # Process events as they arrive
        while self._running:
            try:
                await self._process_events()
            except Exception as e:  # noqa: BLE001
                logger.error("AST ORACLE BLINDED (Transient): %s", e)
            await asyncio.sleep(self.poll_interval)

    async def stop(self) -> None:
        """Closes the Oracle's eye and detaches filesystem hooks."""
        self._running = False
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
        logger.info("AST ORACLE OFFLINE.")

    async def _pre_warm_cache(self) -> None:
        """Initial snapshot of the semantic state (one-time O(N) bootstrap)."""
        for py_file in self.watch_dir.rglob("*.py"):
            target_str = str(py_file)
            if _SKIP_DIRS.intersection(py_file.parts):
                continue

            try:
                mtime = py_file.stat().st_mtime
                self._mtimes[target_str] = mtime
                self._cache[target_str] = self._extract_semantic_nodes(py_file)
            except (ValueError, KeyError, OSError, RuntimeError, AttributeError):
                pass

    async def _process_events(self) -> None:
        """Drain the event queue and process changed files."""
        if self._event_queue is None:
            return

        changed: set[Path] = set()
        while not self._event_queue.empty():
            try:
                changed.add(self._event_queue.get_nowait())
            except asyncio.QueueEmpty:
                break

        for py_file in changed:
            target_str = str(py_file)

            if not py_file.exists():
                # File deleted — purge from memory
                self._mtimes.pop(target_str, None)
                self._cache.pop(target_str, None)
                continue

            try:
                current_mtime = py_file.stat().st_mtime
                old_mtime = self._mtimes.get(target_str, 0.0)

                if current_mtime > old_mtime:
                    self._mtimes[target_str] = current_mtime
                    new_nodes = self._extract_semantic_nodes(py_file)
                    old_nodes = self._cache.get(target_str, set())

                    mutations = self._compute_semantic_diff(old_nodes, new_nodes)
                    if mutations:
                        self._cache[target_str] = new_nodes
                        await self._inject_intent(py_file, mutations)

            except FileNotFoundError:
                self._mtimes.pop(target_str, None)
                self._cache.pop(target_str, None)

    def _extract_semantic_nodes(self, path: Path) -> set[str]:
        """Parses a Python file and returns a set of semantic signatures."""
        try:
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(path))
            return {ast.dump(node) for node in ast.walk(tree)}
        except Exception:  # noqa: BLE001
            return set()

    def _compute_semantic_diff(self, old_nodes: set[str], new_nodes: set[str]) -> list[str]:
        """Compares two syntax trees to infer the magnitude of change."""
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
            project = path.parent.name
            if project == "cortex":
                project = "cortex_engine"

            await self.engine.store(
                project=project,
                content=content,
                fact_type="human_mutation",
                meta={
                    "oracle": "ast_diff_v2",
                    "file_target": str(path),
                    "mutations": mutations,
                    "severity": severity,
                },
            )
            logger.info(
                "🧠 [AST ORACLE] Mutation Collapsed: %s -> %s",
                path.name,
                severity,
            )
        except Exception as e:  # noqa: BLE001
            logger.error("AST Oracle Injection failed on %s: %s", path.name, e)
