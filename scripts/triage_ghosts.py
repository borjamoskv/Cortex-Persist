import asyncio
import os
import sys

# Agregamos cortex al path
sys.path.insert(0, os.path.expanduser("~/cortex"))

from cortex.engine import CortexEngine


async def main():
    async with CortexEngine() as engine:
        print("Buscando ghosts activos...")
        ghosts = await engine.get_all_active_facts(fact_types=["ghost"])

        print(f"\nSe encontraron {len(ghosts)} ghosts en total.")

        by_project = {}

        for g in ghosts:
            project = g.project or "unknown"
            if project not in by_project:
                by_project[project] = []
            by_project[project].append(g)

        print("\n--- REPORTE DE GHOSTS ACTIVOS ---")
        for proj, items in by_project.items():
            print(f"\n[{proj.upper()}] ({len(items)} ghosts)")
            for i, ghost in enumerate(items, 1):
                content = ghost.content or ""
                gid = ghost.id or "?"
                print(f"  {i}. [ID:{gid}] {content}")


if __name__ == "__main__":
    asyncio.run(main())
