import asyncio
from cortex.extensions.llm.router import Router, HedgedRequests

async def main():
    router = Router()
    prompt = """
    Hola Sergio,

    Estoy revisando el código del proyecto Cortex-Persist. ¿Ves alguna fisura de seguridad, 
    problema arquitectónico, o debilidad (ghosts/fissures) en el código actual, 
    específicamente en la implementación de la capa de seguridad, el ledgers, o los guards?
    
    Por favor, sé tan crítico como sea necesario.
    """
    
    # We use HedgedRequests to ask the frontier models (Gemini 3.1 Pro / ChatGPT 5.2 / Claude 4.6)
    # to evaluate the codebase for security fissures, acting as 'Sergio' (or a critical security auditor).
    print("Consultando a Sergio (Frontend Models via Sovereign Router) sobre fisuras de seguridad...")
    
    response = await router.query(
        prompt=prompt,
        intent="security_audit",
        require_frontier=True
    )
    
    print("\nRespuesta de Sergio:")
    print("-" * 80)
    print(response.content)
    print("-" * 80)

if __name__ == "__main__":
    asyncio.run(main())
