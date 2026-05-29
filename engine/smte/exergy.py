import time
from typing import Any, Optional


class ExergyMonitor:
    """
    Measures the thermodynamic 'Exergy' (useful work) vs 'Entropy' (waste/errors)
    of a computational process in the CORTEX environment.
    """

    def __init__(self, target_name: str):
        self.target_name = target_name
        self.start_time = 0.0
        self.end_time = 0.0
        self.status = "UNKNOWN"

    def start_transaction(self):
        self.start_time = time.time()

    def end_transaction(self, success: bool):
        self.end_time = time.time()
        self.status = "C5-REAL" if success else "error"

    def calculate_metrics(self) -> dict[str, Any]:
        latency = self.end_time - self.start_time

        # Base Entropy score (0.0 to 1.0)
        # 1.0 = Total failure (max entropy)
        # 0.0 = Perfect execution (max exergy)
        entropy = 1.0 if self.status != "C5-REAL" else 0.0

        # Penalize high latency (threshold arbitrary for now)
        if latency > 1.0:
            entropy = min(1.0, entropy + 0.2)

        return {
            "target": self.target_name,
            "latency": latency,
            "status": self.status,
            "entropy": entropy,
            "exergy": 1.0 - entropy,
        }


def evaluate_module_exergy(results: list) -> float:
    """
    Takes a list of execution results (e.g. from a stress test) and returns
    the average entropy of the module.
    """
    if not results:
        return 1.0  # Max entropy for no data

    total_entropy = 0.0
    for r in results:
        status = r.get("status")
        latency = r.get("latency", 0.0)

        entropy = 1.0 if status != "C5-REAL" else 0.0
        if latency > 1.0:
            entropy = min(1.0, entropy + 0.2)

        total_entropy += entropy

    return total_entropy / len(results)
