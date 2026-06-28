import asyncio
import sys

from cortex.extensions.llm.router import CortexLLMRouter
from cortex.extensions.swarm.centauro_engine import CentauroEngine, Formation


async def main():
    print("🔱 LEGIØN-1 ACTIVATED - DEPENDABOT SWARM (53 AGENTS)")
    
    # 53 Vulnerabilities -> 53 Agents
    mission = "Auditar y generar remediación para 53 vulnerabilidades Dependabot detectadas en el repositorio (C4-SIM) y proponer parche unificado."
    
    from cortex.extensions.llm.provider import LLMProvider

    primary_provider = LLMProvider("gemini")
    fallback_providers = [
        LLMProvider("openrouter"),
        LLMProvider("deepseek"),
        LLMProvider("ollama"),
        LLMProvider("lmstudio"),
    ]
    router = CortexLLMRouter(primary=primary_provider, fallbacks=fallback_providers)

    engine = CentauroEngine(tolerance=0.67, router=router)

    # Monkey patch formation size dynamically
    CentauroEngine._FORMATION_SIZES["DEPENDABOT"] = 53
    Formation.DEPENDABOT = "DEPENDABOT"

    print(f"MISSION: {mission}")
    print("FORMATION: DEPENDABOT (53 Agents)")
    print("Executing Byzantine Consensus Quorum...")

    try:
        result = await engine.engage(mission=mission, formation="DEPENDABOT")

        print("\n[RESULT]")
        print(f"STATUS: {result.get('status')}")
        print(f"AGENTS USED: {result.get('agents_used')}")
        if "reason" in result:
            print(f"REASON: {result.get('reason')}")
        print("\n[SOLUTION]")
        print(result.get("solution"))

        if result.get("status") == "success":
            sys.exit(0)
        else:
            sys.exit(1)

    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
