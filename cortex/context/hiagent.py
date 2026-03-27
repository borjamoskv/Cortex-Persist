import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

try:
    import structlog
    _HAS_STRUCTLOG = True
    logger = structlog.get_logger(__name__)
except ModuleNotFoundError:
    import logging
    _HAS_STRUCTLOG = False
    logger = logging.getLogger(__name__)


def log_info(msg: str, **kwargs):
    if _HAS_STRUCTLOG:
        logger.info(msg, **kwargs)
    else:
        logger.info(f"{msg} {kwargs}")


def log_debug(msg: str, **kwargs):
    if _HAS_STRUCTLOG:
        logger.debug(msg, **kwargs)
    else:
        logger.debug(f"{msg} {kwargs}")


def log_warning(msg: str, **kwargs):
    if _HAS_STRUCTLOG:
        logger.warning(msg, **kwargs)
    else:
        logger.warning(f"{msg} {kwargs}")

@dataclass
class ObservationTrace:
    timestamp: datetime
    action: str
    observation: str
    metadata: dict[str, Any] = field(default_factory=dict)

class HiAgent:
    """
    Subgoal Compression Engine (Axiom Ω₁₃ Enforcement).
    
    Prevents context collapse by buffering episodic traces during a task block,
    crystallizing them into a single summary, and then forcing 'Amnesia Local'
    on the raw data.
    """
    
    def __init__(self, session_id: str | None = None):
        self.session_id = session_id or str(uuid.uuid4())
        self._trace_buffer: list[ObservationTrace] = []
        self._is_active = False

    def add_trace(self, action: str, observation: str, metadata: dict[str, Any] | None = None):
        """Buffers an action-observation pair."""
        trace = ObservationTrace(
            timestamp=datetime.now(),
            action=action,
            observation=observation,
            metadata=metadata or {}
        )
        self._trace_buffer.append(trace)
        log_debug("Trace added to buffer", session_id=self.session_id, action=action)

    async def crystallize(self) -> str:
        """
        Compresses the buffered traces into a single derivative 'crystal'.
        In a real scenario, this would involve a summary call to a model.
        """
        if not self._trace_buffer:
            return ""
        
        log_info("Crystallizing episodic traces", count=len(self._trace_buffer))
        
        # Simplified deterministic crystallization for now
        summary_lines = [f"- {t.action}: {t.observation[:100]}..." for t in self._trace_buffer]
        crystal = f"Crystallized Subgoal [{self.session_id}]:\n" + "\n".join(summary_lines)
        
        return crystal

    async def flush(self):
        """Forces 'Amnesia Local' - clears raw traces from memory."""
        count = len(self._trace_buffer)
        self._trace_buffer.clear()
        log_warning("Amnesia Local enforced: raw traces flushed", session_id=self.session_id, count=count)

    @asynccontextmanager
    async def subgoal(self, name: str) -> AsyncIterator["HiAgent"]:
        """
        Async context manager for a subgoal execution block.
        Automatically crystallizes and flushes upon exit.
        """
        self._is_active = True
        log_info("Starting subgoal block", name=name)
        try:
            yield self
            # Success: Crystallize
            crystal = await self.crystallize()
            # Here we would normally store the crystal in semantic memory via MemoryOS
            log_info("Subgoal crystal generated", name=name, length=len(crystal))
        finally:
            await self.flush()
            self._is_active = False
            log_info("Exited subgoal block", name=name)

# Example Usage:
# async with HiAgent().subgoal("Refactoring Pipeline") as agent:
#     agent.add_trace("grep", "found 5 instances")
#     # ... logic ...
