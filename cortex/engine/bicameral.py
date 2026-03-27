"""OaxacaEngine — Sovereign CORTEX Engine (High Performance).
Refinement of the Bicameral architecture (Dual Bus).
Ω₁₃: Thermodynamic optimization via asynchronous bus separation.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cortex.engine.isolation import IsolationManager
from cortex.ledger.sovereign_ledger import SovereignLedger

logger = logging.getLogger("cortex.oaxaca")


@dataclass
class EngineConfig:
    db_path: str | Path
    storage_root: str | Path


class BicameralDispatcher:
    """Ω₁₃: Dual Bus Dispatcher for Asynchronous Isolation.

    Routes requests through two parallel channels:
    - 🟢 Fast Path: Non-blocking, in-memory, high-frequency (Search, Graphs).
    - 🟡 Slow Path: Blocking, IO-intensive, auditable (Persistence, Sync).
    """

    def __init__(self):
        self._fast_routes: dict[str, Any] = {}
        self._slow_routes: dict[str, Any] = {}

    def register_fast(self, name: str, handler: Any):
        self._fast_routes[name] = handler

    def register_slow(self, handler: Any):
        # Default slow handler is usually the store/persist method
        self._slow_routes["store"] = handler

    async def dispatch(self, action: str, *args, **kwargs) -> Any:
        """Route the action to the appropriate bus."""
        if action in self._fast_routes:
            return await self._fast_routes[action](*args, **kwargs)

        # Fallback to slow path if it's a store action
        if action == "store" and "store" in self._slow_routes:
            return await self._slow_routes["store"](*args, **kwargs)

        raise ValueError(f"No route registered for action: {action}")


class OaxacaEngine:
    """The High-Performance Sovereign Engine (Oaxaca Layer)."""

    def __init__(self, config: EngineConfig):
        self.config = config
        self.db_path = Path(config.db_path)
        self.storage_root = Path(config.storage_root)

        # Core Components
        self.ledger = SovereignLedger(self.db_path)
        self.isolation = IsolationManager(self)

        self._background_tasks: set[asyncio.Task] = set()

    async def initialize(self):
        """Ω-Boot: Initialize all cognitive and physical subsystems."""
        # Ensure directories exist
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Ledger init is sync for now in the current implementation,
        # but isolation is already pre-initialized.
        logger.info("OaxacaEngine initialized at %s", self.db_path)

    async def shutdown(self):
        """Clean shutdown of all subsystems."""
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        logger.info("OaxacaEngine shutdown complete.")

    def __repr__(self) -> str:
        return f"OaxacaEngine(db={self.db_path})"
