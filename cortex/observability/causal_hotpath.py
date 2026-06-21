# [C5-REAL] Exergy-Maximized
import logging
import math
import time
from collections.abc import Callable
from dataclasses import dataclass

logger = logging.getLogger("cortex.hotpath")


@dataclass
class CausalEdge:
    source: str
    target: str
    exergy: float
    latency: float
    transitions: int


class CausalHotPathInjector:
    def __init__(self, threshold: float = 60.0, lambda_decay: float = 0.5, saturation_cap: int = 5):
        self.threshold = threshold
        self.lambda_decay = lambda_decay
        self.saturation_cap = saturation_cap
        self.handlers: dict[tuple[str, str], Callable] = {}
        # Thermal tracking: stores (activation_count, last_activation_time)
        self.thermal_state: dict[tuple[str, str], tuple[int, float]] = {}

    def register(self, source: str, target: str, handler: Callable):
        """Register a prewarm handler for a specific edge."""
        self.handlers[(source, target)] = handler
        logger.info(f"Registered hot-path handler for edge: {source} -> {target}")

    def evaluate(self, edge: CausalEdge):
        """
        Evaluates the thermal pattern of an edge.
        If the energy score exceeds the Lyapunov threshold, it triggers the registered handler.
        Applies a Causal Dampening Field to prevent runaway execution loops.
        """
        key = (edge.source, edge.target)
        now = time.time()

        # Update and decay thermal state
        activations, last_time = self.thermal_state.get(key, (0, 0.0))

        # Linear decay of activations over time (1 activation cools down every 5 minutes)
        time_delta = now - last_time
        cooldown = int(time_delta / 300.0)
        if cooldown > 0:
            activations = max(0, activations - cooldown)
            # Reset last_time to now so we don't double count if we cooled down
            last_time = now

        # Thermal saturation ceiling
        if activations >= self.saturation_cap:
            logger.warning(
                f"🧯 [CHPI] Thermal saturation reached for {key}. Subgraph activation capped."
            )
            return None

        # Lyapunov stability proxy equation (Base Score)
        base_score = (edge.exergy * 0.7) + (edge.transitions * 5.0) - (edge.latency * 0.01)

        # Causal Dampening Field: weight_new = weight * exp(-λ * activation_frequency)
        dampening_factor = math.exp(-self.lambda_decay * activations)
        dampened_score = base_score * dampening_factor

        if dampened_score >= self.threshold and key in self.handlers:
            self.thermal_state[key] = (activations + 1, now)
            logger.info(
                f"🔥 [CHPI] Thermal threshold breached ({dampened_score:.1f} >= {self.threshold}). Activating anticipatory hook."
            )
            return self.handlers[key](edge)

        # Update state even if not breached so cooldowns keep running properly from the last check
        self.thermal_state[key] = (activations, last_time)
        return None
