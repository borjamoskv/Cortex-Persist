#!/usr/bin/env python3
"""
CORTEX-PERSIST: Swarm Stress Test
---------------------------------
Injects 50 simultaneous tasks into the Autopoiesis Queue to trigger
massive Epistemic Limerence evaluation and Cortisol shockwaves.
"""

import json
import os
import sys

SWARM_QUEUE_FILE = os.getenv("CORTEX_SWARM_QUEUE", "/tmp/cortex_swarm_queue.json")


def ignite_stress_test():
    print("=== INICIANDO STRESS TEST DEL ENJAMBRE C5-REAL ===")
    print(f"Target Queue: {SWARM_QUEUE_FILE}")

    tasks = []
    # Generamos 50 agentes (la mitad sufrirá fricción, la mitad tendrá éxito)
    for i in range(50):
        agent_id = f"Agent_Omega_{i}"
        tasks.append(
            {
                "agent": agent_id,
                "payload": {"action": "solve_topology_entropy", "complexity": i * 10},
            }
        )

    queue_data = {"pending_tasks": tasks}

    with open(SWARM_QUEUE_FILE, "w") as f:
        json.dump(queue_data, f, indent=2)

    print(f"[+] Inyectados {len(tasks)} agentes en el pipeline de Autopulse.")
    print(
        "[+] Ejecuta `python3 cortex/swarm/autopulse.py` para presenciar la detonación topológica."
    )


if __name__ == "__main__":
    ignite_stress_test()
