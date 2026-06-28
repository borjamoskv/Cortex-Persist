# [C5-REAL] Exergy-Maximized
"""CORTEX v6+ - Semantic CRDTs over Zenoh.

Replaces asynchronous stochastic merges with deterministic CRDT operations
for the multi-agent Swarm memory state.
Gracefully degrades to asyncio PubSub if the Zenoh native binary is unavailable.
"""

import asyncio
import json
import logging
from typing import Any, Callable

try:
    import zenoh
    HAS_ZENOH = True
except ImportError:
    HAS_ZENOH = False

from cortex.memory.crdt import CRDTEngram, LWWRegister, GCounter, ORSet

logger = logging.getLogger("cortex.swarm.zenoh_crdt")

class ZenohCRDTBridge:
    """Pub/Sub interface for Swarm-wide CRDT eventual consistency."""
    
    def __init__(self, workspace_prefix: str = "cortex/memory/swarm") -> None:
        self.workspace_prefix = workspace_prefix
        self.session = None
        self._local_bus: asyncio.Queue[tuple[str, str]] = asyncio.Queue()
        self._handlers: list[Callable[[CRDTEngram], None]] = []
        
    async def connect(self) -> None:
        """Establish connection to the Zenoh fabric or local bus."""
        global HAS_ZENOH
        if HAS_ZENOH:
            try:
                conf = zenoh.Config()
                self.session = zenoh.open(conf)
                
                # Subscribe to all Swarm CRDT mutations
                self.sub = self.session.declare_subscriber(
                    f"{self.workspace_prefix}/**", 
                    self._zenoh_callback
                )
                logger.info("[ZenohBridge] Connected to native Zenoh fabric.")
            except Exception as e:
                logger.error(f"[ZenohBridge] Native Zenoh connection failed: {e}. Degrading to async bus.")
                HAS_ZENOH = False
        
        if not HAS_ZENOH:
            logger.info("[ZenohBridge] Running in emulation mode (asyncio bus).")
            asyncio.create_task(self._emulated_dispatch_loop())

    def _zenoh_callback(self, sample: Any) -> None:
        """Callback for incoming Zenoh messages."""
        payload_str = sample.payload.decode("utf-8")
        self._process_payload(payload_str)

    async def _emulated_dispatch_loop(self) -> None:
        """Fallback loop for local emulation."""
        while True:
            try:
                topic, payload_str = await self._local_bus.get()
                self._process_payload(payload_str)
            except Exception as e:
                logger.error(f"[ZenohBridge] Emulation loop error: {e}")

    def _process_payload(self, payload_str: str) -> None:
        """Deserialize and dispatch incoming CRDTEngram."""
        try:
            data = json.loads(payload_str)
            engram = CRDTEngram(engram_id=data["engram_id"])
            engram.content.value = data.get("content_val", "")
            engram.content.timestamp = data.get("content_ts", 0.0)
            
            for k, v in data.get("access_counts", {}).items():
                engram.access_count._counts[k] = v
                
            for k, v in data.get("tags", {}).items():
                engram.tags._elements[k] = v
                
            for handler in self._handlers:
                handler(engram)
                
        except json.JSONDecodeError:
            pass

    def on_sync(self, handler: Callable[[CRDTEngram], None]) -> None:
        """Register a handler to merge incoming CRDTEngrams into local state."""
        self._handlers.append(handler)

    async def publish_mutation(self, engram: CRDTEngram) -> None:
        """Publish a local CRDT mutation to the global Zenoh swarm."""
        payload = {
            "engram_id": engram.engram_id,
            "content_val": engram.content.value,
            "content_ts": engram.content.timestamp,
            "access_counts": engram.access_count._counts,
            "tags": engram.tags._elements
        }
        payload_str = json.dumps(payload)
        topic = f"{self.workspace_prefix}/{engram.engram_id}"
        
        if HAS_ZENOH and self.session is not None:
            self.session.put(topic, payload_str.encode("utf-8"))
            logger.debug(f"[ZenohBridge] Published mutation to Zenoh fabric: {engram.engram_id}")
        else:
            await self._local_bus.put((topic, payload_str))

# Global C5-REAL Bridge Instance
zenoh_bridge = ZenohCRDTBridge()
