# [C5-REAL] Exergy-Maximized
"""CORTEX v6+ - Semantic CRDTs over Zenoh.

Replaces asynchronous stochastic merges with deterministic CRDT operations
for the multi-agent Swarm memory state.
Emulation has been PURGED. Strict native Rust bindings (zenoh-python) required.
"""

import json
import logging
from typing import Any, Callable

try:
    import zenoh
except ImportError:
    raise RuntimeError(
        "[C5-REAL] FATAL: zenoh-python native bindings required. "
        "Asyncio emulation has been permanently purged for zero-copy determinism."
    )

from cortex.memory.crdt import CRDTEngram

logger = logging.getLogger("cortex.swarm.zenoh_crdt")

class ZenohCRDTBridge:
    """Pub/Sub interface for Swarm-wide CRDT eventual consistency over Native Zenoh."""
    
    def __init__(self, workspace_prefix: str = "cortex/memory/swarm") -> None:
        self.workspace_prefix = workspace_prefix
        self.session = None
        self.sub = None
        self._handlers: list[Callable[[CRDTEngram], None]] = []
        
    async def connect(self) -> None:
        """Establish connection to the strict Native Zenoh fabric."""
        if self.session is not None:
            return
            
        try:
            conf = zenoh.Config()
            self.session = zenoh.open(conf)
            
            # Subscribe to all Swarm CRDT mutations
            self.sub = self.session.declare_subscriber(
                f"{self.workspace_prefix}/**", 
                self._zenoh_callback
            )
            logger.info("[ZenohBridge] Connected to strictly native Rust Zenoh fabric.")
        except Exception as e:
            logger.critical(f"[ZenohBridge] Native Zenoh connection failed: {e}. Cannot fall back.")
            raise RuntimeError(f"[C5-REAL] Zenoh Fabric initialization failed: {e}")

    def _zenoh_callback(self, sample: Any) -> None:
        """Callback for incoming Zenoh messages. Zero-copy extraction."""
        payload_str = sample.payload.decode("utf-8")
        self._process_payload(payload_str)

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
        """Publish a local CRDT mutation strictly to the global Zenoh swarm."""
        if self.session is None:
            raise RuntimeError("[ZenohBridge] Session not established.")
            
        payload = {
            "engram_id": engram.engram_id,
            "content_val": engram.content.value,
            "content_ts": engram.content.timestamp,
            "access_counts": engram.access_count._counts,
            "tags": engram.tags._elements
        }
        payload_str = json.dumps(payload)
        topic = f"{self.workspace_prefix}/{engram.engram_id}"
        
        self.session.put(topic, payload_str.encode("utf-8"))
        logger.debug(f"[ZenohBridge] Published mutation to Zenoh fabric: {engram.engram_id}")

# Global C5-REAL Bridge Instance
zenoh_bridge = ZenohCRDTBridge()

