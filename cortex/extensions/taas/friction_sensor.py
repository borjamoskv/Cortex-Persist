# [C5-REAL] Exergy-Maximized
import logging
from typing import Any

from cortex.extensions.taas.market import TaaSMarketplace

logger = logging.getLogger("cortex.taas.friction_sensor")

class FrictionSensor:
    """
    High-resolution telemetry sensor for the TaaS Market.
    Acts as the nervous system for OUROBOROS-∞ to detect when and what to absorb.
    """

    def __init__(self, market: TaaSMarketplace):
        self.market = market

    def get_friction_telemetry(self, time_window_seconds: int = 3600) -> dict[str, Any]:
        """
        Extracts friction data from recent job execution results.
        Provides OUROBOROS-∞ with the precise locations of cognitive/computational waste.
        """
        # In a fully deployed state, we would filter by `executed_at` within `time_window_seconds`.
        # For now, we process all available in-memory results.
        
        total_latency = 0.0
        total_redundancy = 0.0
        total_memory_blocks = 0.0
        job_count = 0

        for _, result in self.market._results.items():
            if result.friction_metrics:
                total_latency += result.friction_metrics.get("latency_ms", 0)
                total_redundancy += result.friction_metrics.get("llm_redundancy", 0)
                total_memory_blocks += result.friction_metrics.get("memory_blocks", 0)
                job_count += 1

        if job_count == 0:
            return {
                "status": "IDLE",
                "average_latency_ms": 0.0,
                "average_llm_redundancy": 0.0,
                "average_memory_blocks": 0.0,
                "friction_level": "LOW",
                "recommended_action": "SLEEP"
            }

        avg_latency = total_latency / job_count
        avg_redundancy = total_redundancy / job_count
        avg_memory_blocks = total_memory_blocks / job_count

        # Determine overall friction level
        friction_level = "LOW"
        action = "SLEEP"

        if avg_latency > 500 or avg_redundancy > 2.0 or avg_memory_blocks > 5.0:
            friction_level = "CRITICAL"
            action = "OURO_TRANSCEND"
        elif avg_latency > 200 or avg_redundancy > 1.0 or avg_memory_blocks > 2.0:
            friction_level = "MODERATE"
            action = "OURO_ABSORB"

        telemetry = {
            "status": "ACTIVE",
            "jobs_analyzed": job_count,
            "average_latency_ms": avg_latency,
            "average_llm_redundancy": avg_redundancy,
            "average_memory_blocks": avg_memory_blocks,
            "friction_level": friction_level,
            "recommended_action": action
        }

        logger.info(f"[FrictionSensor] Telemetry generated: {friction_level} Friction detected.")
        return telemetry
