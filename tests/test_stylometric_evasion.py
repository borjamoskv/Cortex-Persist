import pytest

from cortex.extensions.llm._models import BaseProvider
from cortex.extensions.llm.router import CortexLLMRouter
from cortex.extensions.llm.stylometry import StylometricEvasionModule


class MockProvider(BaseProvider):
    @property
    def provider_name(self):
        return "mock"

    @property
    def model_name(self):
        return "mock"

    @property
    def context_window(self):
        return 8192

    async def invoke(self, prompt):
        # Verify the system prompt is assembled correctly.
        assert (
            "INSTRUCCIÓN SOBERANA (Módulo NO-IA-Omega / Evasión Estilométrica):"
            in prompt.system_instruction
        )
        return "El rollo este del hacking te quema vivo. Pero mira esto de la entropia."


@pytest.mark.asyncio
async def test_stylometric_evasion_no_ia_omega_prompt():
    router = CortexLLMRouter(primary=MockProvider())
    stylometry = StylometricEvasionModule(router)

    payload = "La entropía cognitiva es fundamental para la seguridad del sistema."
    context = {"title": "Consejos", "topic": "Hacking", "avg_length": "corta", "tone": "calle"}

    result = await stylometry.obfuscate_payload(payload, context)

    assert "rollo este del hacking" in result
    assert result != payload  # Ensure it actually "mutated" it
