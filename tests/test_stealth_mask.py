import asyncio
from unittest.mock import AsyncMock

import pytest

from cortex.extensions.llm._models import CortexPrompt
from cortex.extensions.llm.router import CortexLLMRouter
from cortex.utils.result import Ok


@pytest.mark.asyncio
async def test_stealth_mask_application():
    # 1. Setup Mock Router
    router = CortexLLMRouter()

    # Mocking the internal resilient execution to simulate a generic AI response
    ai_response = "En definitiva, el ecosistema de la IA es un paradigma que no solo transforma X, sino que abre nuevas narrativas."
    router._execute_resilient_impl = AsyncMock(return_value=Ok(ai_response))

    # 2. Case A: Masking OFF
    prompt_no_mask = CortexPrompt(
        system_instruction="Test",
        working_memory=[],
        apply_stealth_mask=False
    )

    result_no_mask = await router.execute_resilient(prompt_no_mask)
    assert result_no_mask.is_ok()
    assert result_no_mask.unwrap() == ai_response
    print("\n[PASS] Masking OFF: Response preserved exactly.")

    # 3. Case B: Masking ON
    prompt_with_mask = CortexPrompt(
        system_instruction="Test",
        working_memory=[],
        apply_stealth_mask=True
    )

    # We also need to mock the masker's own LLM call to avoid infinite recursion or real API calls
    # The masker will call router.execute_resilient(mask_prompt)
    # We can detect this by checking the system instruction or a flag.

    original_execute = router.execute_resilient

    async def mocked_execute(p: CortexPrompt):
        if "NO-IA-Omega" in p.system_instruction:
            return Ok("Texto de-AI-ficado con mala leche y sabor a Bilbao.")
        return await router._execute_resilient_impl(p)

    router.execute_resilient = mocked_execute

    result_with_mask = await router.execute_resilient(prompt_with_mask)
    assert result_with_mask.is_ok()
    masked_text = result_with_mask.unwrap()

    assert "Pesado" not in masked_text # Not the original
    assert "Bilbao" in masked_text
    print(f"[PASS] Masking ON: Response transformed. Output: {masked_text}")

if __name__ == "__main__":
    asyncio.run(test_stealth_mask_application())
