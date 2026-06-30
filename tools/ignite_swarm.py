#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
"""
cat_id: "ignite-swarm"
cat_type: "script"
version: "1.0.0"
reality_level: "C5-REAL"
owner: "borjamoskv"
exergy_tier: "P2"

Swarm 10k Ignition Protocol (Phase 2).
Queries CortexEngine for 'type:ghost' and dispatches them to SwarmCommander.
Falls back to 50 synthetic ghosts if none exist to validate thermodynamic limits.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from babylon60.engine import CortexEngine
from babylon60.engine.swarm_10k import SwarmCommander
from babylon60.extensions.swarm.auto_fix import AutoFixPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ignite_swarm")

@dataclass
class SyntheticGhost:
    id: str
    description: str
    project: str = "CORTEX"

async def fetch_or_generate_ghosts() -> list[Any]:
    db = CortexEngine()
    try:
        await db.initialize()
        results = await db.search("type:ghost", limit=50)
        if results:
            logger.info(f"Found {len(results)} physical ghosts in CORTEX.")
            return results
    except Exception as e:
        logger.warning(f"Could not read physical DB ({e}). Generating synthetics.")

    # Synthetic Generation
    logger.info("Generating 50 synthetic ghosts for Swarm Ignition Validation...")
    ghosts = []
    for i in range(50):
        if i % 3 == 0:
            desc = "TypeError: 'NoneType' object is not callable in runtime execution."
        elif i % 3 == 1:
            desc = "ImportError: cannot import name 'xyz' from 'abc' (circular import)"
        else:
            desc = "FileNotFoundError: configuration 'settings.json' not found."
            
        ghosts.append(SyntheticGhost(id=f"synth-{i}", description=desc))
    
    return ghosts

async def main():
    print("🚀 INICIANDO IGNICIÓN DEL SWARM 10k (FASE 2)")
    start_time = time.perf_counter()

    # 1. Fetch ghosts
    raw_ghosts = await fetch_or_generate_ghosts()
    
    # 2. Transform to tasks via AutoFixPipeline
    pipeline = AutoFixPipeline()
    tasks = []
    for g in raw_ghosts:
        ghost_id = getattr(g, "id", str(id(g)))
        desc = getattr(g, "description", str(g))
        cls = pipeline.classify(desc)
        task = pipeline.ghost_to_task(ghost_id, desc, cls)
        # Add domain based on classification to distribute across Legions
        task["domain"] = f"fix_{cls.value}"
        tasks.append(task)
        
    print(f"🧬 Generadas {len(tasks)} tareas ejecutables. Preparando SwarmCommander...")

    # 3. Ignite Swarm
    test_bus_dir = Path("/tmp/cortex_ignition_bus")
    if test_bus_dir.exists():
        import shutil
        shutil.rmtree(test_bus_dir)
    test_bus_dir.mkdir()

    commander = SwarmCommander(bus_path=test_bus_dir, use_shm=False)
    await commander.initialize()
    
    print(f"📡 Bus soberano inicializado con {commander.bus.num_shards} shards.")
    print("🌪️ Despachando tareas (Bucketed Dispatch con Control Cinético)...")
    
    dispatch_start = time.perf_counter()
    # 4. Dispatch with bucket size 10 to avoid instant overload with heavy autofix tasks
    await commander.execute_bucketed_dispatch(tasks, bucket_size=10)
    dispatch_time = time.perf_counter() - dispatch_start
    
    print(f"✅ Despacho paralelo completado en {dispatch_time:.4f}s")
    print(f"📊 Latencia media de enrutamiento: {(dispatch_time / len(tasks)) * 1000:.4f}ms por tarea")
    
    report = await commander.get_density_report()
    print(f"📈 Reporte de Densidad Termodinámica: {report}")
    
    if report["agents"] == len(tasks):
        print("💎 HOMEOSTASIS CONFIRMADA: 100% de agentes cristalizados y despachados.")
    else:
        print(f"⚠️ DIVERGENCIA: {report['agents']} agentes en L2 vs {len(tasks)} tareas solicitadas.")
    
    print("🧹 Aniquilando y consolidando estado...")
    await commander.consolidate_and_annihilate()
    
    total_time = time.perf_counter() - start_time
    print(f"🚀 FASE 2 COMPLETADA EN {total_time:.2f}s")

if __name__ == "__main__":
    asyncio.run(main())
