import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from cortex.llm.router import CortexRouter
from cortex.llm.models import Message

async def main():
    try:
        router = CortexRouter()
        prompt = """
        ACTÚA COMO SERGIO:
        
        Hola Sergio,
        
        Soy Borja. Tienes razón en que hay fisuras en el sistema, pero ten en cuenta que es mi primer proyecto 
        de GitHub en serio y estoy aprendiendo sobre la marcha. 
        "Sólo sé que no sé nada".
        
        Ya he parcheado la Fisura 3 (El bypass de Tenant-Isolation del ABAC) para cerrarlo de una vez.
        
        Aconséjame el mejor y único siguiente paso más crítico para alguien que está aprendiendo pero 
        que quiere una infraestructura sólida, con el tono crítico pero constructivo que te caracteriza. 
        """
        
        print("Enviando mensaje a Sergio...")
        response = await router.chat(
            messages=[Message(role="user", content=prompt)],
            require_frontier=True
        )
        print("\nRespuesta de Sergio:\n" + "-"*80)
        print(response.content)
        print("-" * 80)
    except Exception as e:
        print(f"Error al conectar: {e}")

if __name__ == "__main__":
    asyncio.run(main())
