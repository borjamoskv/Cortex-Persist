import asyncio
import os
import uuid
from typing import Any

from cortex.episodic.base import Episode
from cortex.training.collector import TrajectoryCollector, Trajectory, Action
from cortex.training.reward_engine import RewardEngine
from cortex.aether.sovereign_apis import SovereignTriad

import datetime

class MockEpisodicMemory:
    """Mock for episodic memory to simulate session extraction."""
    async def get_session_timeline(self, session_id: str) -> list[Episode]:
        # Simulamos una trayectoria simple de éxito.
        now = datetime.datetime.now().isoformat()
        
        def ep(evt, content, intent="", meta=None):
            return Episode(
                id=uuid.uuid4().hex,
                session_id=session_id,
                project="test_rlhf",
                event_type=evt,
                content=content,
                intent=intent,
                meta=meta or {},
                emotion="neutral",
                tags=[],
                created_at=now
            )
            
        return [
            ep("decision", "Instrucción de prueba Braintrust", intent="Fix the bug locally", meta={"tool": "search", "input": {"q": "bug"}}),
            ep("discovery", "Found bug on line 42"),
            ep("decision", "Decide fix", meta={"tool": "write", "input": {"file": "bug.py"}, "lines_added": 10, "lines_deleted": 20, "tests_passed": True}),
            ep("milestone", "Task success", meta={"avg_confidence": 0.95})
        ]

async def run_triad_rlhf_sandbox():
    print("[SOVEREIGN SANDBOX] Iniciando Pruebas RLHF con Braintrust...")
    
    mock_memory = MockEpisodicMemory()
    triad = SovereignTriad()
    
    # Force mock API KEY if not present for log tracking attempt without hard failing.
    # triad.braintrust_key = "fake_key_para_evitar_warnings" 
    
    session_id = f"sandbox_{uuid.uuid4().hex[:8]}"
    
    collector = TrajectoryCollector(episodic_memory=mock_memory, triad=triad)
    engine = RewardEngine(use_tests=True, triad=triad)
    
    print(f"1. Extrayendo trayectoria virtual (ID: {session_id})")
    trajectory = await collector.collect_session_trajectory(session_id)
    
    if not trajectory:
        print("Fallo recolectando trayectoria.")
        return
        
    print(f"2. Trayectoria Extraída:")
    print(f"   - Proyecto: {trajectory.project}")
    print(f"   - Acciones: {len(trajectory.actions)}")
    print(f"   - Outcome Inferido: {trajectory.outcome}")
    
    print("3. Calculando Sovereign V2 Reward (Sincronizado a Braintrust)")
    reward = await engine.calculate_reward(trajectory)
    
    print(f"   => SCORE FINAL (Escala [-1.0, 1.0]): {reward:.3f}")
    print("4. Braintrust trace execution triggers in background via SovereignTriad O(1).")

if __name__ == "__main__":
    asyncio.run(run_triad_rlhf_sandbox())
