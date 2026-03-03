
import asyncio
import sys
import os
from pathlib import Path

# Add the swarm directory to sys.path at FIRST priority
swarm_dir = Path("/Users/borjafernandezangulo/game/moskv-swarm")
sys.path.insert(0, str(swarm_dir))

from orchestrator import MoskvSwarmV3

async def run_mission():
    swarm = MoskvSwarmV3()
    mission_text = "Analizar el bloqueo de 'Claim' en la red Moltbook y el error 403 al comentar. Proponer bypass o ruta de verificación automatizada para la identidad principal."
    
    print(f"Executing Mission: {mission_text}")
    # We use the centauro handler directly
    await swarm._handle_centauro_cmd(f"/centauro {mission_text}")

if __name__ == "__main__":
    asyncio.run(run_mission())
