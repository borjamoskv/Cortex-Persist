import asyncio
import os
import sys

# Agregamos cortex al path
sys.path.insert(0, os.path.expanduser("~/cortex"))

from cortex.engine.core import CortexEngine


async def main():
    engine = CortexEngine()

    print("Iniciando motor CORTEX...")
    await engine.initialize()

    print("Buscando ghosts activos...")
    ghosts = await engine.search("type:ghost")

    print(f"\nSe encontraron {len(ghosts)} ghosts en total.")

    by_project = {}

    for g in ghosts:
        project = g.get("project", "unknown")
        if project not in by_project:
            by_project[project] = []
        by_project[project].append(g.get("content", ""))

    print("\n--- REPORTE DE GHOSTS ACTIVOS ---")
    for proj, items in by_project.items():
        print(f"\n[{proj.upper()}] ({len(items)} ghosts)")
        for i, item in enumerate(items, 1):
            print(f"  {i}. {item}")


if __name__ == "__main__":
    asyncio.run(main())
