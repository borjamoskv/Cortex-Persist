import json
from datetime import datetime, timezone
from typing import Any

from babylon60.database.belief_store import BeliefStore
from babylon60.embeddings.local import LocalEmbedder
from babylon60.engine.causal.belief_objects import (
    BeliefObject,
    BeliefState,
    PropositionPayload,
    ProvenanceEnvelope,
    RelationType,
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
        """Ejecuta una fase atómica asíncrona inyectando el linaje (agent_role)."""
        # Mutamos el estado para simular la ejecución de la fase
        output_data = dict(input_data)
        output_data[f"{phase_name}_completed"] = True
        output_data["current_phase"] = phase_name
        output_data["agent_role"] = agent_role

        data_str = json.dumps(output_data, sort_keys=True)
        
        belief = BeliefObject(
            id=f"{phase_name}_{hash(data_str)}",
            state=BeliefState.VERIFIED,
            relation=RelationType.ENTAILS,
            provenance=ProvenanceEnvelope(
                agent_id=f"DecaCore_{agent_role}",
                session_id="flujo_glorioso_session",
                timestamp=datetime.now(timezone.utc),
                signature=f"CORTEX-TAINT:{agent_role}:{hash(data_str)}",
            ),
            payload=PropositionPayload(
                content=data_str, context_hash=f"{phase_name}_ctx", certainty=1.0
            ),
        )

        embedding = self.embedder.embed(data_str)
        await self.store.insert_belief(belief, embedding)
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
            self.concepcion, self.visualizacion, self.sonido, self.animacion,
            self.voz, self.lipsync, self.edicion, self.vfx, self.upscaling, self.despliegue
        ]
        
        for phase in phases:
            belief = await phase(current_state)
            trajectory.append(belief)
            current_state = json.loads(belief.payload.content)
            
        return trajectory
