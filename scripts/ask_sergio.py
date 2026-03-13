import sys
import os
import asyncio

# Ensure cortex is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cortex.llm.router import CortexRouter
from cortex.llm.models import Message

async def main():
    try:
        router = CortexRouter()
        prompt = """
        ACTÚA COMO SERGIO:
        
        Hola Sergio,

        Estoy revisando el código del proyecto Cortex-Persist. ¿Ves alguna fisura de seguridad en el código, 
        problema arquitectónico, o debilidad (ghosts/fissures) en el código actual de este repositorio, 
        específicamente en la implementación de la capa de seguridad, el ledgers, o los guards?
        
        Por favor, sé tan crítico como sea necesario. Saca a relucir cualquier posible vulnerabilidad por pequeña que sea.
        """
        
        print("Consultando a Sergio (Modelos Frontier vía Router CORTEX) sobre fisuras de seguridad...\n")
        
        # Using a direct call to the router. Depending on the exact API of CortexRouter
        response = await router.chat(
            messages=[Message(role="user", content=prompt)],
            require_frontier=True
        )
        
        print("Respuesta de Sergio:")
        print("-" * 80)
        print(response.content)
        print("-" * 80)
        
    except Exception as e:
        print(f"Error al consultar: {e}")

if __name__ == "__main__":
    asyncio.run(main())
