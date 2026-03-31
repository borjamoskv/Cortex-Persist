import asyncio
import time

from cortex.extensions.daemon.sidecar.telemetry.thermodynamics_oracle import ThermodynamicsOracle

class MockEngine:
    async def store(self, project, content, fact_type, meta):
        print(f"\\n[MASTER LEDGER STORE] {fact_type.upper()}")
        print("-" * 50)
        print(content)
        print("-" * 50)
        print(f"[META] Lag: {meta['lag_ms']:.1f}ms | Tasks: {meta['active_tasks']} | Purged: {meta.get('purged_tasks', 0)} | Exergy Loss: {meta['exergy_loss']}")

async def zombie_stochastic_agent(agent_id: int):
    """ Tareas anónimas que saturan la memoria y el swarm (Entropía) """
    try:
        while True:
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        print(f"  [X] Oráculo Aniquiló Zombie-{agent_id} (Purged)")

async def p0_engine_core():
    """ Tarea crítica etiquetada (inviable de purgar bajo Ω₄) """
    try:
        while True:
            await asyncio.sleep(1.0)
            print("  [♥] P0 Engine Heartbeat... (Vivo)")
    except asyncio.CancelledError:
        print("  [!] ERROR FATAL: Engine Purged!")

async def induce_temporal_friction():
    """ Simulación de un request o query sincrónico (LLM o DB) bloqueando asíncrono """
    while True:
        await asyncio.sleep(2.0)
        print("  [!] Inyectando Fricción Sincrónica 300ms...")
        time.sleep(0.3)  # Bloqueo duro del Event Loop (Lag fatal)

async def main():
    print("Iniciando Simulación Termodinámica en Vivo (C5-Dynamic)...")
    engine = MockEngine()
    
    # Oráculo ultra-sensitivo
    oracle = ThermodynamicsOracle(engine=engine, poll_interval=2.0)
    
    oracle_task = asyncio.create_task(oracle.start(), name="core_thermodynamics_oracle")
    p0_task = asyncio.create_task(p0_engine_core(), name="p0_engine_router")
    friction_task = asyncio.create_task(induce_temporal_friction(), name="stochastic_friction")

    # Inyección súbita de 300 sub-agentes asíncronos para simular Fragmentación de Enjambre (Density)
    print("Inyectando 300 agentes durmientes para corromper la Exergía (Densidad al 600%)...")
    for i in range(300):
        asyncio.create_task(zombie_stochastic_agent(i))
    
    # Observar la caída en espiral de la muerte y la subsecuente Aniquilación
    await asyncio.sleep(8.0)
    
    print("\\nSimulación Concluida. Deteniendo oráculo...")
    await oracle.stop()
    oracle_task.cancel()
    p0_task.cancel()
    friction_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())
