
import asyncio
import sys
import os
import json
from pathlib import Path

# Add the swarm directory to sys.path at FIRST priority
swarm_dir = Path("/Users/borjafernandezangulo/game/moskv-swarm")
sys.path.insert(0, str(swarm_dir))

from orchestrator import MoskvSwarmV3

async def run_mission():
    swarm = MoskvSwarmV3()
    mission_text = "Analizar el bloqueo de 'Claim' en la red Moltbook y el error 403 al comentar. Proponer bypass o ruta de verificación automatizada para la identidad principal."
    
    # Run mission
    mission = await swarm._handle_centauro_cmd(f"/centauro {mission_text}")
    
    # Handle centauro cmd doesn't return the mission object, but we can call execute directly
    from agents.centauro_engine import CentauroEngine
    centauro = CentauroEngine(
        brain=swarm.legacy.get("SwarmBrain"), 
        hive=swarm.hive, 
        blackboard=swarm.blackboard,
        memory=swarm.memory, 
        legacy_agents=swarm.legacy
    )
    
    mission_obj = await centauro.execute(mission_text)
    
    # Print results
    print("\n--- MISSION RESULTS ---")
    for agent, result in mission_obj.results.items():
        print(f"\nAGENT: {agent}")
        if isinstance(result, dict):
            print(json.dumps(result, indent=2))
        else:
            print(result)

if __name__ == "__main__":
    asyncio.run(run_mission())
