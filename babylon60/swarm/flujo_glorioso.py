import json
from datetime import datetime, timezone
from typing import Any

from babylon60.database.belief_store import BeliefStore
from babylon60.embeddings.local import LocalEmbedder
from babylon60.engine.causal.belief_objects import (
    BeliefObject,
    BeliefState,
    ProvenanceEnvelope,
    BeliefRelations,
)


class DecaCoreOrchestrator:
    """
    Orquestador Deca-Core para el workflow Flujo Glorioso v2.
    Operando bajo modo C5-REAL (Fail-Fast Termodinámico, Async Non-Blocking).
    """

    def __init__(self, store: BeliefStore, embedder: LocalEmbedder | None = None):
        self.store = store
        self.embedder = embedder or LocalEmbedder()

    async def _execute_phase(self, phase_name: str, agent_role: str, input_data: dict[str, Any]) -> BeliefObject:
        from decimal import Decimal
        from babylon60.engine.core.ultrathink_physics import UltrathinkPhysicsEngine
        from babylon60.engine.entropy import EntropyAnnihilator

        """Ejecuta una fase atómica asíncrona inyectando el linaje (agent_role)."""
        import time
        start_time = time.monotonic()

        # Mutamos el estado para simular la ejecución de la fase
        output_data = dict(input_data)
        output_data[f"{phase_name}_completed"] = True
        output_data["current_phase"] = phase_name
        output_data["agent_role"] = agent_role

        data_str = json.dumps(output_data, sort_keys=True)
        input_str = json.dumps(input_data, sort_keys=True)

        execution_time = max(0.001, time.monotonic() - start_time)

        stochastic_entropy = max(0.1, UltrathinkPhysicsEngine.estimate_shannon_entropy(input_str))
        deterministic_output = max(0.1, UltrathinkPhysicsEngine.estimate_shannon_entropy(data_str))

        # Termodinámica: Calcular Exergy Yield (L12 - Fail-Fast Termodinámico)
        exergy_yield = UltrathinkPhysicsEngine.calculate_exergy_yield(stochastic_entropy, deterministic_output, execution_time)
        if exergy_yield < 0.1:
            annihilator = EntropyAnnihilator()
            annihilator.execute_apoptosis_on_rot(rot_score=Decimal(1.0 - exergy_yield))
            raise RuntimeError(f"Fallo Termodinámico: Exergía insuficiente en fase {phase_name} ({exergy_yield:.2f}). Apoptosis invocada.")

        # Entropía determina la tasa de decaimiento (Anergía penalizada)
        dynamic_decay = 0.05 / deterministic_output

        embedding = self.embedder.embed(data_str)
        
        belief = BeliefObject(
            belief_id=f"{phase_name}_{hash(data_str)}",
            proposition=data_str,
            semantic_embedding=embedding,
            state=BeliefState.ACTIVE,
            confidence_score=1.0,
            variance=0.0,
            decay_rate=dynamic_decay,
            provenance=ProvenanceEnvelope(
                source_hash=f"{phase_name}_ctx",
                source_type="agent",
                tenant_id="SYSTEM",
                signer_id=f"DecaCore_{agent_role}",
                signature=f"CORTEX-TAINT:{agent_role}:{hash(data_str)}",
                created_at=datetime.now(timezone.utc).isoformat(),
                was_generated_by="flujo_glorioso_session"
            ),
            relations=BeliefRelations(
                entails=[],
                discards=[]
            )
        )

        await self.store.insert_belief(belief)
        return belief

    async def concepcion(self, input_data: dict[str, Any]) -> BeliefObject:
        return await self._execute_phase("concepcion", "Musa", input_data)

    async def visualizacion(self, input_data: dict[str, Any]) -> BeliefObject:
        return await self._execute_phase("visualizacion", "Musa", input_data)

    async def sonido(self, input_data: dict[str, Any]) -> BeliefObject:
        return await self._execute_phase("sonido", "Musa", input_data)

    async def animacion(self, input_data: dict[str, Any]) -> BeliefObject:
        return await self._execute_phase("animacion", "Musa", input_data)

    async def voz(self, input_data: dict[str, Any]) -> BeliefObject:
        return await self._execute_phase("voz", "Musa", input_data)

    async def lipsync(self, input_data: dict[str, Any]) -> BeliefObject:
        return await self._execute_phase("lipsync", "Arquitecto", input_data)

    async def edicion(self, input_data: dict[str, Any]) -> BeliefObject:
        return await self._execute_phase("edicion", "Arquitecto", input_data)

    async def vfx(self, input_data: dict[str, Any]) -> BeliefObject:
        return await self._execute_phase("vfx", "Musa", input_data)

    async def upscaling(self, input_data: dict[str, Any]) -> BeliefObject:
        return await self._execute_phase("upscaling", "Arquitecto", input_data)

    async def despliegue(self, input_data: dict[str, Any]) -> BeliefObject:
        return await self._execute_phase("despliegue", "Comandante", input_data)

    async def execute_genesis(self, initial_concept: str) -> list[BeliefObject]:
        """
        Inicia el Flujo Glorioso v2.0 completo en cascada asíncrona.
        El payload de cada fase se inyecta como entrada de la siguiente.
        """
        trajectory = []
        current_state = {"idea": initial_concept}
        
        phases = [
            "concepcion", "visualizacion", "sonido", "animacion",
            "voz", "lipsync", "edicion", "vfx", "upscaling", "despliegue"
        ]
        
        for phase_name in phases:
            method = getattr(self, phase_name)
            belief = await method(current_state)
            trajectory.append(belief)
            current_state = json.loads(belief.proposition)
            
        return trajectory
