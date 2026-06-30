# [C5-REAL] Exergy-Maximized
import time
from dataclasses import dataclass, field

import numpy as np
from babylon60.observability.exergy_engine import ExecutionTrace

MAX_FAILURE_REVENUE_MULTIPLIER = 3.0
SYSTEM_REFLEX_TIME_SEC = 300  # Δt (billing -> execution) must be > 5 min


@dataclass
class BillingTrace:
    task: str
    base_ssu: float
    monetized_entropy: float
    revenue_multiplier: float
    timestamp: float = field(default_factory=time.time)


class DualLedger:
    def __init__(self):
        self.execution_ledger: list[ExecutionTrace] = []
        self.billing_ledger: list[BillingTrace] = []

    def clamp_entropy(self, entropy: float) -> float:
        return float(min(entropy, 1.0))

    def stabilized_ssu(self, base_ssu: float, history: list[float]) -> float:
        if not history:
            return base_ssu
        drift = np.std(history[-100:])
        return float(base_ssu / (1.0 + drift))

    def process_execution(self, trace: ExecutionTrace):
        # 1. Store in Execution Ledger (Reality)
        self.execution_ledger.append(trace)

        # 2. Delayed translation to Billing Ledger (Economy)
        # We calculate the economics, but they do NOT feed back to the execution
        # field generator immediately. They are insulated in the billing ledger.

        entropy_signal = self.clamp_entropy(trace.fdf_shift)

        # Guard against runaway failure optimization
        multiplier = min(1.0 + entropy_signal, MAX_FAILURE_REVENUE_MULTIPLIER)

        # Extract historical costs for this task
        historical_costs = [t.real_cost for t in self.execution_ledger if t.task == trace.task]

        stable_ssu = self.stabilized_ssu(trace.real_cost, historical_costs)

        bill = BillingTrace(
            task=trace.task,
            base_ssu=stable_ssu,
            monetized_entropy=entropy_signal,
            revenue_multiplier=multiplier,
        )

        self.billing_ledger.append(bill)

    def get_lagged_economic_feedback(self) -> dict[str, float]:
        """
        Ouroboros Engine Safety Rule:
        Only return economic signals that are older than SYSTEM_REFLEX_TIME_SEC.
        This prevents the system from directly optimizing its own failure generation.
        """
        current_time = time.time()
        safe_horizon = current_time - SYSTEM_REFLEX_TIME_SEC

        safe_bills = [b for b in self.billing_ledger if b.timestamp < safe_horizon]

        # Compute delayed economic pressure
        pressure = {}
        for b in safe_bills:
            if b.task not in pressure:
                pressure[b.task] = []
            pressure[b.task].append(b.revenue_multiplier * b.base_ssu)

        return {task: float(np.mean(vals)) for task, vals in pressure.items()}


class OuroborosEngine:
    """
    Self-stabilizing computational organism.
    Computation, error, and cost co-evolve under delayed feedback dynamics.
    """

    def __init__(self):
        self.ledger = DualLedger()

    def inject_telemetry(self, trace: ExecutionTrace):
        self.ledger.process_execution(trace)

    def get_safe_optimization_signal(self) -> dict[str, float]:
        """Returns the delayed economic distortion to safely feed into the Exergy Field."""
        return self.ledger.get_lagged_economic_feedback()
