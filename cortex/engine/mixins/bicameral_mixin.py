"""Bicameral Mixin — CORTEX v8.0.
Interfaces the Engine with the BicameralDispatcher.
"""

from __future__ import annotations

import logging
from typing import Any

from cortex.engine.bicameral import BicameralDispatcher

logger = logging.getLogger("cortex.engine.bicameral")


class BicameralMixin:
    """Extension for CortexEngine to support dual-bus dispatching."""

    def __init__(self):
        super().__init__()
        self.dispatcher = BicameralDispatcher()
        self._setup_bicameral_routes()

    def _setup_bicameral_routes(self):
        """Map standard engine operations to the Bicameral Dispatcher."""
        # Note: Actual mapping happens after other mixins are initialized
        # to ensure method references are valid.
        pass

    async def bicameral_store(self, *args, **kwargs) -> Any:
        """Store a fact via the Bicameral Dispatcher."""
        return await self.dispatcher.dispatch("store", *args, **kwargs)

    async def bicameral_search(self, *args, **kwargs) -> Any:
        """Search facts via the Bicameral Dispatcher."""
        return await self.dispatcher.dispatch("search", *args, **kwargs)
