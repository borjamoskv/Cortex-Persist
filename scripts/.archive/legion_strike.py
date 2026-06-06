import argparse
import asyncio
import sys

from cortex.extensions.swarm.centauro_engine import CentauroEngine


async def main():
    parser = argparse.ArgumentParser(description="LEGIØN-1 Sovereign Swarm Protocol Strike Interface")
    parser.add_argument("--mission", required=True, help="Mission objective for the Swarm")
    parser.add_argument("--formation", default="BLITZ", choices=[
        "BLITZ", "PHALANX", "SIEGE", "HYDRA", "ORACLE", "PHOENIX", "CHIMERA", 
        "LEVIATHAN", "OUROBOROS", "SENTINEL", "SPECTRE", "GHOST"
    ], help="Tactical formation to deploy")
    parser.add_argument("--tolerance", type=float, default=0.67, help="Byzantine consensus tolerance")
    
    args = parser.parse_args()

    engine = CentauroEngine(tolerance=args.tolerance)
    
    print("🔱 LEGIØN-1 ACTIVATED")
    print(f"MISSION: {args.mission}")
    print(f"FORMATION: {args.formation}")
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
