from dataclasses import dataclass
from typing import Callable, Dict, Tuple
import logging

logger = logging.getLogger("cortex.hotpath")

@dataclass
class CausalEdge:
    source: str
    target: str
    exergy: float
    latency: float
    transitions: int

class CausalHotPathInjector:
    def __init__(self, threshold: float = 60.0):
        self.threshold = threshold
        self.handlers: Dict[Tuple[str, str], Callable] = {}

    def register(self, source: str, target: str, handler: Callable):
        """Register a prewarm handler for a specific edge."""
        self.handlers[(source, target)] = handler
        logger.info(f"Registered hot-path handler for edge: {source} -> {target}")

    def evaluate(self, edge: CausalEdge):
        """
        Evaluates the thermal pattern of an edge.
        If the energy score exceeds the Lyapunov threshold, it triggers the registered handler.
        """
        key = (edge.source, edge.target)

        # Lyapunov stability proxy equation
        # Heavily weights transitions (reinforcement) and dampens highly latent connections
        score = (edge.exergy * 0.7) + (edge.transitions * 5.0) - (edge.latency * 0.01)

        if score >= self.threshold and key in self.handlers:
            logger.info(f"[CHPI] Thermal threshold breached ({score:.1f} >= {self.threshold}). Activating anticipatory hook.")
            return self.handlers[key](edge)

        return None
