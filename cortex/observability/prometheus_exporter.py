# [C5-REAL] Exergy-Maximized
import time

from prometheus_client import Counter, Gauge, Histogram  # pyright: ignore[reportMissingImports]

# --- CORTEX SYSTEM METRICS ---

CORTEX_EXERGY = Gauge(
    "cortex_system_exergy_total", "Current Exergy Level (Usable Energy) of the Cortex System"
)
CORTEX_ENTROPY = Gauge(
    "cortex_system_entropy_total", "Current Entropy Level (Disorder) of the Cortex System"
)
CORTEX_COST = Gauge("cortex_system_billing_ssu", "Current Economic Cost (SSU) of the Cortex System")
CORTEX_DRIFT = Gauge(
    "cortex_system_drift_variance", "Causal Drift (Divergence between Execution and Billing)"
)

CORTEX_EXECUTION_COUNT = Counter(
    "cortex_execution_cycles_total", "Total number of execution cycles processed"
)

CORTEX_ACTION_LATENCY = Histogram("cortex_action_latency_seconds", "Latency of autonomous actions")


class CortexPrometheusExporter:
    @staticmethod
    def update_metrics(state_dict: dict):
        """
        Updates Prometheus gauges based on the current SystemState.
        """
        CORTEX_EXERGY.set(state_dict.get("exergy", 0.0))
        CORTEX_ENTROPY.set(state_dict.get("entropy", 0.0))
        CORTEX_COST.set(state_dict.get("cost", 0.0))
        CORTEX_DRIFT.set(state_dict.get("drift", 0.0))

        CORTEX_EXECUTION_COUNT.inc()

    @staticmethod
    def track_latency(start_time: float):
        """
        Tracks execution latency for the Histogram.
        """
        latency = time.time() - start_time
        CORTEX_ACTION_LATENCY.observe(latency)
