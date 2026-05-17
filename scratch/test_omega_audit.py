"""
CORTEX — Sovereign Exploit Substrate (Ω) Test Analysis.

Target: liquidation-engine/src/calculation.rs
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from cortex.guards.mythos_auditor import MythosAuditor
from cortex.forensics.models import MythosClaim, Severity, HazardClass


async def main():
    print("--- INICIANDO SIMULACIÓN DE REALIDAD ADVERSARIAL (Ω) ---")

    # Read the target code
    target_path = "/Users/borjafernandezangulo/10_PROJECTS/2026-04-k2/contracts/liquidation-engine/src/calculation.rs"
    with open(target_path) as f:
        code = f.read()

    auditor = MythosAuditor()

    # For testing, we'll inject a simulated Torpedo hypothesis
    # to see how the scoring and containment work.
    # Hypothesis: Oracle Lag Manipulation allowing unbacked value extraction.
    test_claim = MythosClaim(
        fact_id="ORACLE-LAG-01",
        hypothesis="Attacker can exploit delay between price_oracle and market state to liquidate healthy accounts.",
        exploit_vector="t0: manipulate oracle price; t1: trigger calculate_liquidation; t2: profit from bonus.",
        severity=Severity.CRITICAL,
        suggested_hazard=HazardClass.H3,
        agent_id="torpedo-test",
    )

    # We patch _generate_claims for the test to return our simulated claim
    async def mocked_claims(*args, **kwargs):
        return [test_claim]

    auditor._generate_claims = mocked_claims

    # Run Analysis
    artifacts = await auditor.analyze_target(code, "liquidation-engine")

    for art in artifacts:
        print(f"\n[FORENSIC ARTIFACT: {art.claim.fact_id}]")
        print(f"Hypothesis: {art.claim.hypothesis}")
        print(f"Mathematical Exploitability (E): {art.exploitability.score:.2f}")
        print(f"Judgment: {art.judgment.reality.value} | {art.judgment.is_verified}")

        print("\n[PRIVILEGE TOPOLOGY]")
        for node in art.privilege_map.nodes:
            print(f" - ROLE: {node.role} | CAPABILITIES: {node.capabilities}")

        for path in art.privilege_map.reachable_escalation_paths:
            print(f" ! {path}")

        print(f"\n[ANATHEMA STATUS]: {art.get_hazard_class().value}")


if __name__ == "__main__":
    asyncio.run(main())
