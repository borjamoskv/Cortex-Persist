import asyncio

from cortex.extensions.llm._models import BaseProvider, CortexPrompt, IntentProfile, ReasoningMode
from cortex.extensions.llm.router import CortexLLMRouter


class MockProvider(BaseProvider):
    def __init__(self, name: str, cost: str, tier: str):
        self._name = name
        self._cost_class = cost
        self._tier = tier

    @property
    def provider_name(self) -> str:
        return self._name

    @property
    def model_name(self) -> str:
        return self._name

    @property
    def cost_class(self) -> str:
        return self._cost_class

    @property
    def tier(self) -> str:
        return self._tier

    async def invoke(self, prompt):
        return "mock"


async def test_reasoning_modes():
    # Setup dummy providers with different tiers
    openrouter = MockProvider("openrouter", "medium", "frontier")
    deepseek = MockProvider("deepseek", "low", "frontier")
    groq = MockProvider("groq", "free", "high")
    local_llama = MockProvider("local_llama", "free", "local")

    router = CortexLLMRouter(
        primary=groq,  # high tier
        fallbacks=[openrouter, deepseek, local_llama],
    )

    # 1. Normal prompt
    prompt_normal = CortexPrompt(
        system_instruction="Normal",
        working_memory=[{"role": "user", "content": "hello"}],
        intent=IntentProfile.GENERAL,
    )
    fallbacks_normal = router._ordered_fallbacks(prompt_normal)
    print("Normal Fallbacks:", [p.provider_name for p in fallbacks_normal])

    # 2. ULTRA_THINK prompt
    prompt_ultra = CortexPrompt(
        system_instruction="Ultra",
        working_memory=[{"role": "user", "content": "solve universe"}],
        intent=IntentProfile.GENERAL,
        reasoning_mode=ReasoningMode.ULTRA_THINK,
    )
    fallbacks_ultra = router._ordered_fallbacks(prompt_ultra)
    print("Ultra Fallbacks:", [p.provider_name for p in fallbacks_ultra])


if __name__ == "__main__":
    asyncio.run(test_reasoning_modes())
