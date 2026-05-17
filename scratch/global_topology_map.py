"""
CORTEX — Global Attack Surface Mapper (Ω).

Maps the privilege topology across the entire 10_PROJECTS workspace.
"""

import asyncio
import os
import sys
import time

# Add project root to path
sys.path.append(os.getcwd())

from cortex.guards.mythos_auditor import MythosAuditor

CRITICAL_PROJECTS = [
    "2026-04-k2",
    "moonwell-strike-2026",
    "cortex-persist",
    "firedancer",
    "sp1",
    "cortex-sentinel",
]


async def map_project_topology(auditor, project_path):
    project_name = os.path.basename(project_path.strip("/"))
    print(f"[*] Analizando Topología: {project_name}...")

    # Identify entry points (simplified)
    entry_points = []
    for root, _dirs, files in os.walk(project_path):
        for file in files:
            if file in [
                "lib.rs",
                "main.rs",
                "contract.rs",
                "contract.sol",
                "index.ts",
                "engine.py",
            ]:
                entry_points.append(os.path.join(root, file))

    topology_summary = []
    for ep in entry_points[:5]:  # Cap at 5 entry points for the global sweep
        try:
            with open(ep) as f:
                code = f.read()

            # We only run the privilege mapper for the global sweep to avoid LLM costs
            # and focus on structural boundaries.
            graph = auditor._priv_mapper.map_privileges(code)

            summary = {
                "file": os.path.relpath(ep, project_path),
                "nodes": [n.role for n in graph.nodes],
                "escalations": graph.reachable_escalation_paths,
            }
            topology_summary.append(summary)
        except Exception:
            continue

    return {"project": project_name, "topology": topology_summary}


async def main():
    print("--- INICIANDO MAPEO GLOBAL DE SUPERFICIE DE ATAQUE (Ω) ---")
    auditor = MythosAuditor()
    root_dir = "/Users/borjafernandezangulo/10_PROJECTS"

    start_time = time.time()

    tasks = []
    for p in CRITICAL_PROJECTS:
        p_path = os.path.join(root_dir, p)
        if os.path.exists(p_path):
            tasks.append(map_project_topology(auditor, p_path))

    results = await asyncio.gather(*tasks)

    print("\n--- MATRIZ DE PRIVILEGIOS GLOBAL ---")
    for r in results:
        print(f"\n[PROYECTO: {r['project']}]")
        for t in r["topology"]:
            print(f"  ├─ Archivo: {t['file']}")
            print(f"  │  └─ Roles: {', '.join(t['nodes'])}")
            if t["escalations"]:
                for e in t["escalations"]:
                    print(f"  │  ! ALERTA ESCALADA: {e}")
        if not r["topology"]:
            print("  └─ (No se detectaron puntos de entrada estándar)")

    print(f"\nMapeo completado en {time.time() - start_time:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
