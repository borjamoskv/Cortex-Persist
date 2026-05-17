import asyncio
import logging
import sys
import os

# Añadir el path del proyecto para importar cortex
sys.path.append(os.getcwd())

from cortex.engine.nine_router_agent import NineRouterAgent


async def test_inference():
    logging.basicConfig(level=logging.INFO)
    print("🚀 Iniciando C4-SIMULACIÓN: Test de Túnel 9Router + Qwen")

    agent = NineRouterAgent(tenant_id="test-tenant", project_id="test-project", model="cortex-fast")

    try:
        # Intento de inferencia simple
        print("📡 Enviando señal al proxy 9Router...")
        result = await agent.execute_task(
            prompt="Genera una firma SHA3 para un bloque vacío.",
            system_prompt="Eres un nodo de CORTEX.",
        )
        print(f"✅ Respuesta recibida:\n{result}")
    except Exception as e:
        print(
            f"❌ Fallo de conexión (Es probable que 9Router no esté corriendo en el puerto 20128): {e}"
        )


if __name__ == "__main__":
    asyncio.run(test_inference())
