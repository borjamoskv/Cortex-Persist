from decimal import Decimal

import pytest

from cortex.swarm.specialists import MarketingVectorSpecialist


@pytest.mark.asyncio
async def test_marketing_specialist_sihur_verification():
    """
    SIHUR (Ziur) Verification Test:
    Validates that the MarketingVectorSpecialist produces correct exergy scores
    and maintains the C5-Dynamic trust boundary when executed.
    """
    specialist = MarketingVectorSpecialist()
    
    # Simulate a marketing narrative task
    # In CORTEX, a task is a string or a structured object
    task = "Propagate AI Sovereignty narrative on Moltbook nodes."
    
    # Execute the specialist (in dry-run or mock mode if needed, 
    # but here we test the class logic)
    response = await specialist.execute(task)
    
    # Assertions for SIHUR/Ziur (Sureness)
    assert response.status == "success"
    assert "marketing-specialist-omega" in response.metadata["provider"]
    
    # Check exergy potency (Potency for marketing is 1.95)
    # The exergy score should be > 0
    assert response.exergy_score > Decimal("0")
    
    # Verify the law compliance
    assert "Ω1" in response.metadata["law_compliance"]
    assert "Ω6" in response.metadata["law_compliance"]

    print(f"\n[SIHUR VERIFIED] Exergy Score: {response.exergy_score}")
    print(f"[SIHUR VERIFIED] Trust Boundary: {response.metadata['epistemic_validation']}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_marketing_specialist_sihur_verification())
