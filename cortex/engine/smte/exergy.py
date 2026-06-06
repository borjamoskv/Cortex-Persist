# [C5-REAL] Exergy-Maximized
import logging
import time
from typing import Any

logger = logging.getLogger("cortex.engine.smte.exergy")

# Configurable thresholds (AX-047 enforcement)
LIMERENCE_CIRCUIT_BREAKER_THRESHOLD: float = 20.0
DEAD_CODE_RATIO_THRESHOLD: float = 0.4
LIMERENCE_PENALTY_MULTIPLIER: float = 10.0


class CircuitBreakerTripped(Exception):
    """Raised when the limerence penalty trips the exergy circuit breaker."""
    pass


class ExergyMonitor:
    """
    Measures the thermodynamic 'Exergy' (useful work) vs 'Entropy' (waste/errors)
    of a computational process in the CORTEX environment.
    Ouroboros-Omega L-EPI Guard integrated.
    """

    def __init__(
        self,
        target_name: str,
        *,
        circuit_breaker_threshold: float = LIMERENCE_CIRCUIT_BREAKER_THRESHOLD,
        dead_code_threshold: float = DEAD_CODE_RATIO_THRESHOLD,
        penalty_multiplier: float = LIMERENCE_PENALTY_MULTIPLIER,
    ):
        self.target_name = target_name
        self.start_time = 0.0
        self.end_time = 0.0
        self.status = "UNKNOWN"
        self.ast_complexity = 1.0  # Default baseline
        self.empirical_usage = 1.0  # Default baseline
        self.dead_code_ratio = 0.0  # Default baseline
        self._circuit_breaker_threshold = circuit_breaker_threshold
        self._dead_code_threshold = dead_code_threshold
        self._penalty_multiplier = penalty_multiplier
        self._tripped = False

    def set_l_epi_metrics(
        self, ast_complexity: float, empirical_usage: float, dead_code_ratio: float
    ):
        self.ast_complexity = ast_complexity
        self.empirical_usage = max(0.001, empirical_usage)  # Prevent div by zero
        self.dead_code_ratio = dead_code_ratio

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

        # Ouroboros-Omega Formula
        limerence_penalty = (
            (self.ast_complexity / self.empirical_usage) * self._penalty_multiplier
        )

        # Circuit Breaker (AX-047): abort mutation loop if limerence is catastrophic
        if limerence_penalty > self._circuit_breaker_threshold:
            self._tripped = True
            logger.critical(
                "CIRCUIT BREAKER TRIPPED for '%s': limerence_penalty=%.2f > threshold=%.2f. "
                "Mutation loop MUST abort.",
                self.target_name,
                limerence_penalty,
                self._circuit_breaker_threshold,
            )
            raise CircuitBreakerTripped(
                f"Circuit breaker tripped: limerence penalty {limerence_penalty:.2f} "
                f"exceeds threshold {self._circuit_breaker_threshold:.2f}"
            )

        must_amputate = (
            self.dead_code_ratio > self._dead_code_threshold
            and limerence_penalty > self._penalty_multiplier
        )

        return {
            "target": self.target_name,
            "latency": latency,
            "status": self.status,
            "entropy": entropy,
            "exergy": 1.0 - entropy,
            "limerence_penalty": limerence_penalty,
            "dead_code_ratio": self.dead_code_ratio,
            "circuit_breaker_tripped": self._tripped,
            "must_amputate": must_amputate,
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
