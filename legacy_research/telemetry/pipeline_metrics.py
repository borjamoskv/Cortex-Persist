# [C5-REAL] Exergy-Maximized
"""
Pipeline Metrics Tracker
Enforces concrete operational thresholds for multi-model orchestrations.
Replaces abstract "cognitive exergy" with strict, measurable SLA checks.
"""

import time
import logging

logger = logging.getLogger("cortex.telemetry.pipeline_metrics")

class PipelineThresholds:
    PRECISION_MIN = 0.90
    COST_PER_CLAIM_MAX = 0.08
    LOOP_RATE_MAX = 0.15
    LATENCY_P95_MAX = 45.0
    HALLUCINATION_RATE_MAX = 0.05

class PipelineMetrics:
    def __init__(self):
        self.start_time = time.time()
        self.total_claims = 0
        self.confirmed_claims = 0
        self.total_cost_usd = 0.0
        self.total_loops = 0
        self.total_steps = 0
        self.uncited_claims = 0

    def record_cost(self, usd_amount: float):
        self.total_cost_usd += usd_amount

    def record_loop(self):
        self.total_loops += 1

    def record_step(self):
        self.total_steps += 1

    def record_claim(self, confirmed: bool, cited: bool):
        self.total_claims += 1
        if confirmed:
            self.confirmed_claims += 1
        if not cited:
            self.uncited_claims += 1

    def compute_metrics(self) -> dict:
        latency = time.time() - self.start_time
        precision = (self.confirmed_claims / self.total_claims) if self.total_claims > 0 else 1.0
        cost_per_claim = (self.total_cost_usd / self.total_claims) if self.total_claims > 0 else 0.0
        loop_rate = (self.total_loops / self.total_steps) if self.total_steps > 0 else 0.0
        hallucination_rate = (self.uncited_claims / self.total_claims) if self.total_claims > 0 else 0.0

        return {
            "precision": precision,
            "cost_per_claim": cost_per_claim,
            "loop_rate": loop_rate,
            "latency_p95": latency,
            "hallucination_rate": hallucination_rate
        }

    def validate_thresholds(self):
        m = self.compute_metrics()
        logger.info(f"Pipeline Metrics: {m}")

        if m["precision"] < PipelineThresholds.PRECISION_MIN:
            logger.warning(f"Precision SLA violated: {m['precision']} < {PipelineThresholds.PRECISION_MIN}")
        if m["cost_per_claim"] > PipelineThresholds.COST_PER_CLAIM_MAX:
            logger.warning(f"Cost SLA violated: {m['cost_per_claim']} > {PipelineThresholds.COST_PER_CLAIM_MAX}")
        if m["loop_rate"] > PipelineThresholds.LOOP_RATE_MAX:
            logger.warning("Loop Rate SLA violated. Review JSON Schema of Stage 3 and Few-Shot of Stage 2.")
        if m["latency_p95"] > PipelineThresholds.LATENCY_P95_MAX:
            logger.warning(f"Latency SLA violated: {m['latency_p95']} > {PipelineThresholds.LATENCY_P95_MAX}")
        if m["hallucination_rate"] > PipelineThresholds.HALLUCINATION_RATE_MAX:
            logger.warning("Hallucination SLA violated. Forcing stronger citation-grounding in Stage 5.")
