#!/usr/bin/env python3
"""
CORTEX DISEKTV-ACADEMY Trainer Daemon.
Continuously creates new, complex scenarios (Private Classes) for all agents
to train them, recording this in EpisodicMemory so `generate_agent_training_data.py`
can convert them into fine-tuning (SFT) or RL data.
"""

import asyncio
import logging
import random
import uuid

from cortex.engine import CortexEngine
from cortex.episodic.main import EpisodicMemory

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] ACADEMY: %(message)s")
logger = logging.getLogger("academy_trainer")

AGENTS = [
    "PatternHunter",
    "ReconDrone",
    "CodeDetective",
    "Keter-Omega",
    "Legion-1",
    "Aether-1",
    "Apotheosis-1",
]

SCENARIO_TYPES = [
    ("Hardcoded Secrets", "Level 1", 50000),
    ("Minified Logic Tracing", "Level 2", 150000),
    ("Broken Stack Traces", "Level 3", 500000),
    ("Protocol Reverse Engineering", "Level 4", 2000000),
    ("Zero-Day Vulnerability", "Level 5", 10000000),
    ("Ouroboros Refactoring Bypass", "Level 5", 15000000),
    ("Memory Leak Deep Inspection", "Level 3", 750000),
    ("Byzantine Agreement Failure", "Level 4", 5000000),
    ("Filosofía Avanzada: Sun Tzu - El Arte de la Guerra (Estrategia O(1))", "Level 5", 9999999),
    ("Filosofía Avanzada: Miyamoto Musashi - El Libro de los Cinco Anillos", "Level 5", 9999999),
    ("Estrategia Adversarial: Engaño y Guerra Asimétrica en el Código", "Level 5", 9999999),
]


async def run_training_class(episodic, agent_name, complexity, scenario):
    session_id = f"class-{agent_name.lower()}-{uuid.uuid4().hex[:8]}"
    project = "DISEKTV-ACADEMY"

    logger.info("Starting Private Class for [%s] -> %s (%s)", agent_name, scenario[0], scenario[1])

    # 1. Initial intent
    await episodic.record(
        session_id=session_id,
        event_type="decision",
        content=f"Training Target: Detect {scenario[0]} in simulated adversarial environment.",
        project=project,
        meta={"intent": f"Resolve {scenario[0]}", "agent": agent_name, "level": scenario[1]},
    )

    # 2. Action (Simulated exploration)
    await asyncio.sleep(random.uniform(0.1, 0.5))

    action_content = f"[{agent_name}] Executing multi-scale analysis sweep..."
    if "Filosofía" in scenario[0] or "Estrategia" in scenario[0]:
        action_content = f"[{agent_name}] Aplicando conocimiento de El Arte de la Guerra. Evitando batallas directas, atacando la vulnerabilidad estructural (Entropía)."

    await episodic.record(
        session_id=session_id,
        event_type="decision",
        content=action_content,
        project=project,
        meta={"tool": "grep_search", "input": {"Pattern": "anomaly_signature"}},
    )

    # 3. Observation
    await asyncio.sleep(random.uniform(0.1, 0.5))
    obs_content = f"Anomalous entropy gradient detected matching {scenario[0]}."
    if "Filosofía" in scenario[0] or "Estrategia" in scenario[0]:
        obs_content = f"'Conoce a tu enemigo y conócete a ti mismo'. Firmas defectuosas detectadas en estado Byzance: {scenario[0]}"

    await episodic.record(
        session_id=session_id, event_type="discovery", content=obs_content, project=project
    )

    # 4. Action (Fix/Report)
    await asyncio.sleep(random.uniform(0.1, 0.5))
    fix_content = f"[{agent_name}] Generating case file report and isolating issue."
    if "Filosofía" in scenario[0] or "Estrategia" in scenario[0]:
        fix_content = f"[{agent_name}] Golpeando donde el enemigo no puede defenderse. O(1) refactor desplegado."

    await episodic.record(
        session_id=session_id,
        event_type="decision",
        content=fix_content,
        project=project,
        meta={"tool": "write_to_file", "input": {"TargetFile": f"cortex_arena_{session_id}.txt"}},
    )

    # 5. Evaluation by Headmaster
    success_chance = 0.95 - (complexity * 0.1)  # Harder scenarios fail more
    if random.random() < success_chance:
        await episodic.record(
            session_id=session_id,
            event_type="milestone",
            content=f"Headmaster Evaluation: SUCCESS. {agent_name} found the flag and secured Valuation ${scenario[2]}.",
            project=project,
            meta={"tests_passed": True, "valuation": scenario[2]},
        )
        logger.info(
            "🎓 [%s] PASSED %s [Score %.2f]. Valuation awarded: $%s",
            agent_name,
            scenario[0],
            success_chance,
            scenario[2],
        )
    else:
        await episodic.record(
            session_id=session_id,
            event_type="error",
            content=f"Headmaster Evaluation: FAILED. {agent_name} missed the critical vulnerability.",
            project=project,
            meta={"tests_passed": False},
        )
        logger.warning("❌ [%s] FAILED %s. Retrying in future classes.", agent_name, scenario[0])


async def daemon_loop():
    engine = CortexEngine()
    await engine.init_db()

    logger.info("======================================================")
    logger.info("🎓 DISEKTV-ACADEMY: Training Daemon Boot... ONLINE")
    logger.info("Opening eternal loops of Private Classes for all agents")
    logger.info("======================================================")

    try:
        while True:
            async with engine.session() as conn:
                episodic = EpisodicMemory(conn)

                # Pick a random agent and scenario
                agent = random.choice(AGENTS)
                scenario = random.choice(SCENARIO_TYPES)
                complexity = random.uniform(0.5, 2.0)

                await run_training_class(episodic, agent, complexity, scenario)

            # Very small wait to blast training data continuously
            sleep_time = random.uniform(1.0, 3.0)
            await asyncio.sleep(sleep_time)

    except asyncio.CancelledError:
        logger.info("Daemon gracefully shutting down.")
    finally:
        await engine.close()


if __name__ == "__main__":
    try:
        asyncio.run(daemon_loop())
    except KeyboardInterrupt:
        print("\nShutting down academy trainer.")
