import pytest
import asyncio
import time
from cortex.engine.rhizome_mesh import RhizomeMesh

@pytest.mark.asyncio
async def test_rhizome_mesh_non_hierarchical_routing_h_rhizome_01():
    mesh = RhizomeMesh()
    execution_log = []
    
    # 1. Definimos los nodos autónomos (Especialistas)
    async def log_agent_1(payload):
        await asyncio.sleep(0.1) # Simulando I/O
        execution_log.append(f"Agent1 processed: {payload}")
        
    async def log_agent_2(payload):
        await asyncio.sleep(0.2)
        execution_log.append(f"Agent2 processed: {payload}")
        
    # 2. Desterritorialización: Los nodos se unen pasivamente a la malla (sin orquestador)
    mesh.subscribe("DATA_MINED", log_agent_1)
    mesh.subscribe("DATA_MINED", log_agent_2)
    
    # 3. Disparo del Evento Rizomático
    start_time = time.time()
    await mesh.publish("DATA_MINED", "user_records_batch_01")
    duration = time.time() - start_time
    
    # 4. Validaciones Estructurales
    assert len(execution_log) == 2
    assert "Agent1 processed: user_records_batch_01" in execution_log
    assert "Agent2 processed: user_records_batch_01" in execution_log
    
    # 5. Validación Termodinámica:
    # Si la ejecución fuera arborescente sincrónica (Parent -> A1 -> A2), tardaría > 0.3s.
    # Al ser concurrente asíncrona, el tiempo total está determinado por el cuello de botella más largo (~0.2s).
    # Verificamos que la latencia se reduce (Concurrencia sin bloqueo).
    assert duration < 0.25  # H-RHIZOME-01: Reducción de latencia por ejecución concurrente.
