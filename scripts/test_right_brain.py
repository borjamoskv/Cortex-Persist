# [C5-REAL] Exergy-Maximized
import logging
from cortex.extensions.evolution.free_energy import FreeEnergyState
from cortex.extensions.evolution.agents import AgentDomain
from cortex.engine.right_brain import HeuristicEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_daydreaming_test():
    engine = HeuristicEngine()

    # Ingest ambient noise (ambient buffer)
    engine.ingest_ambient_signal({"source": "vision_sensor_1", "tag": "blue_light"})
    engine.ingest_ambient_signal({"source": "audio_sensor_2", "tag": "high_pitch"})
    engine.ingest_ambient_signal({"source": "memory_bank_A", "tag": "past_trauma"})
    engine.ingest_ambient_signal({"source": "market_feed", "tag": "price_spike"})

    logger.info("--- Test 1: High Surprise / Left Brain Dominance ---")
    state_stressed = FreeEnergyState(domain=AgentDomain.FABRICATION, surprise=0.8, free_energy=1.2)
    insights = engine.daydream(state_stressed)
    logger.info(f"Insights generated: {len(insights)}")  # Expected 0

    logger.info("\n--- Test 2: Low Surprise / Right Brain Daydreaming ---")
    state_relaxed = FreeEnergyState(domain=AgentDomain.FABRICATION, surprise=0.1, free_energy=0.2)
    insights = engine.daydream(state_relaxed)
    for i, insight in enumerate(insights):
        logger.info(f"Insight {i + 1}: {insight}")


if __name__ == "__main__":
    run_daydreaming_test()
