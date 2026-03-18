import asyncio
import json
import logging
from pathlib import Path

from cortex.engine.core import CortexEngine
from cortex.extensions.swarm.infinite_minds import InfiniteMindsManager
from cortex.extensions.swarm.orchestrator_deep_think import DeepThinkOrchestrator

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    engine = CortexEngine()
    await engine.initialize()

    minds_manager = InfiniteMindsManager()

    orchestrator = DeepThinkOrchestrator(engine, minds_manager)

    report_path = Path("CORTEX_DORKING_REPORT.json")
    if not report_path.exists():
        print("❌ Report CORTEX_DORKING_REPORT.json not found.")
        return

    data = json.loads(report_path.read_text())

    context = (
        "ANOMALY REPORT FROM GITHUB DORKING AGENT:\n"
        f"Found {len(data)} potential secrets/vulnerabilities.\n"
        "Most of them are located in `.venv/lib/python3.12/site-packages/`.\n"
        "Analyze these findings. Are they false positives? What is the real impact and mitigation?\n"
    )

    print("🌊 Iniciando inyección de onda a los 10 Astros (Deep Think)...")
    final_truth = await orchestrator.pulse(context, project="CORTEX_SECURITY_AUDIT")

    print("\n\n" + "=" * 50)
    print("⚡ [DEEP THINK] SÍNTESIS FINAL (MARADONA_10_OMEGA)")
    print("=" * 50)
    print(final_truth)
    print("=" * 50 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
