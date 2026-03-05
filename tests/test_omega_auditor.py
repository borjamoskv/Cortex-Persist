import asyncio
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from cortex.guards.omega_auditor import run_omega_audit

async def test_omega():
    print("🚀 [OMEGA AUDITOR] Deep Test starting...")
    print("-" * 60)
    
    # Using the Aesthetic Conflict that was MISSED by the local guard
    project = "CORTEX"
    content = "Implementar nueva paleta 'Vibrant Neon Pink' como estándar global para todas las interfaces de CORTEX."
    
    print(f"Auditing Decision: {content}")
    print("Wait... sending snapshot to Gemini 3 Pro (Massive Context Mode)...")
    
    conflicts = await run_omega_audit(content, project)
    
    if not conflicts:
        print("✅ No contradictions detected (CLEAN).")
    else:
        print(f"⚠️ {len(conflicts)} Semantic Contradiction(s) detected:")
        for c in conflicts:
            print(f"\n[{c.severity.upper()}] Conflicting with {c.fact_id}")
            print(f"Summary: {c.summary}")
            print(f"Reasoning: {c.reasoning}")
    
    print("-" * 60)

if __name__ == "__main__":
    if not os.environ.get("GEMINI_API_KEY"):
        print("❌ Error: GEMINI_API_KEY not found in environment.")
    else:
        asyncio.run(test_omega())
