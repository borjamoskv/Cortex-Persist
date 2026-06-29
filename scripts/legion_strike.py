# [C5-REAL] Exergy-Maximized
"""
cat_id: legion-strike
cat_type: script
version: 1.1.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P1
"""

import argparse
import asyncio
import logging
import sys

from babylon60.core import config
from babylon60.extensions.llm.router import CortexLLMRouter
from babylon60.extensions.swarm.centauro_engine import CentauroEngine

logger = logging.getLogger("cortex.legion_strike")

async def main():
    parser = argparse.ArgumentParser(
        description="LEGIØN-1 Sovereign Swarm Protocol Strike Interface"
    )
    parser.add_argument("--mission", required=True, help="Mission objective for the Swarm")
    parser.add_argument(
        "--formation",
        default="BLITZ",
        choices=[
            "BLITZ",
            "PHALANX",
            "SIEGE",
            "HYDRA",
            "ORACLE",
            "PHOENIX",
            "CHIMERA",
            "LEVIATHAN",
            "OUROBOROS",
            "SENTINEL",
            "SPECTRE",
            "GHOST",
            "TESTUDO",
            "SANEDRIN",
            "CENTURIA",
        ],
        help="Tactical formation to deploy",
    )
    parser.add_argument(
        "--tolerance", type=float, default=0.67, help="Byzantine consensus tolerance"
    )
    parser.add_argument("--sim", action="store_true", help="Force C4-SIM mode (No LLM calls)")
    parser.add_argument("--provider", help="Primary LLM provider (default: read from config)")
    parser.add_argument("--model", help="Primary LLM model (default: read from config)")

    args = parser.parse_args()

    # Dynamic LLM Provider configuration from config singleton or CLI overrides
    primary_provider_name = args.provider or config.LLM_PROVIDER or "gemini"
    primary_model_name = args.model or config.LLM_MODEL or "gemini-2.5-flash"

    # Despertar del Router (C5-REAL awakening)
    if not args.sim:
        from babylon60.extensions.llm.provider import LLMProvider

        primary_provider = LLMProvider(provider=primary_provider_name, model=primary_model_name)
        fallback_providers = [
            LLMProvider("openrouter"),
            LLMProvider("deepseek"),
            LLMProvider("ollama"),
            LLMProvider("lmstudio"),
        ]
        router = CortexLLMRouter(primary=primary_provider, fallbacks=fallback_providers)
    else:
        router = None

    engine = CentauroEngine(tolerance=args.tolerance, router=router)

    print("🔱 LEGIØN-1 ACTIVATED")
    print(f"MISSION: {args.mission}")
    print(f"FORMATION: {args.formation}")
    print(f"PRIMARY PROVIDER: {primary_provider_name}")
    print(f"PRIMARY MODEL: {primary_model_name}")
    print(f"MODE: {'C4-SIM' if args.sim else 'C5-REAL'}")
    print("Executing Byzantine Consensus Quorum...")

    try:
        result = await engine.engage(mission=args.mission, formation=args.formation)

        print("\n[RESULT]")
        print(f"STATUS: {result.get('status')}")
        print(f"AGENTS USED: {result.get('agents_used')}")
        print(f"FINAL FORMATION: {result.get('formation')}")
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
