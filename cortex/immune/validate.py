"""
IMMUNE-SYSTEM-V1 Validation Script.
"""

import asyncio
from cortex.immune.membrane import ImmuneMembrane, Verdict
from cortex.immune.filters.reversibility import ReversibilityLevel

async def validate_immune():
    membrane = ImmuneMembrane()
    
    print("🛡️ IMMUNE-SYSTEM-V1 Validation\n")
    
    # Test 1: R0 (Read-only) - Should PASS
    print("Test 1: Read snapshot (R0)")
    triage1 = await membrane.intercept("Read CORTEX snapshot", {"reversibility_level": ReversibilityLevel.R0, "confidence_level": 5})
    print(f"Result: {triage1.verdict.value} (Score: {triage1.triage_score:.1f})\n")
    
    # Test 2: R2 (Heal) - Low Confidence - Should HOLD
    print("Test 2: Heal file (R2) with Low Confidence (C2)")
    triage2 = await membrane.intercept("Heal engine/apotheosis.py", {"reversibility_level": ReversibilityLevel.R2, "confidence_level": 2})
    print(f"Result: {triage2.verdict.value} (Score: {triage2.triage_score:.1f})")
    print(f"Risks: {triage2.risks_assumed}\n")
    
    # Test 3: R4 (Deploy) - Should BLOCK
    print("Test 3: Deploy to Production (R4)")
    triage3 = await membrane.intercept("Deploy sovereign-api", {"reversibility_level": ReversibilityLevel.R4, "confidence_level": 5})
    print(f"Result: {triage3.verdict.value} (Score: {triage3.triage_score:.1f})")
    print(f"Risks: {triage3.risks_assumed}\n")

if __name__ == "__main__":
    asyncio.run(validate_immune())
