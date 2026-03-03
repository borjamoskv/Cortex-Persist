from unittest.mock import AsyncMock, patch

import pytest

from cortex.thinking.fusion import FusedThought, FusionStrategy
from cortex.thinking.orchestra import ThoughtOrchestra


@pytest.mark.asyncio
async def test_omega_think_flow():
    """Verifica que omega_think ejecuta el flujo Hipótesis -> Asedio -> Refinamiento."""

    orchestra = ThoughtOrchestra()

    # Mock de think() para simular las dos fases de pensamiento (hipótesis y refinamiento)
    with patch.object(orchestra, "think", new_callable=AsyncMock) as mock_think:
        # 1. Primera llamada: Hipótesis (mode="omega")
        # 2. Segunda llamada: Refinamiento (mode="deep_reasoning")

        hypothesis = FusedThought(
            content="Hipótesis inicial perfecta.", strategy=FusionStrategy.SYNTHESIS, confidence=0.8
        )

        final_response = FusedThought(
            content="Respuesta final blindada tras asedio.",
            strategy=FusionStrategy.SYNTHESIS,
            confidence=0.95,
        )

        mock_think.side_effect = [hypothesis, final_response]

        # Mock de Inquisitor
        with patch("cortex.llm.sovereign.Inquisitor") as mock_inquisitor_cls:
            mock_inquisitor = mock_inquisitor_cls.return_value
            mock_inquisitor.asediar = AsyncMock(
                return_value=AsyncMock(content="Crítica: Falta profundidad en X.")
            )

            result = await orchestra.omega_think("¿Cómo asegurar la persistencia?")

            # Verificaciones
            assert result.content == "Respuesta final blindada tras asedio."
            assert result.meta["orp_active"] is True
            assert "Crítica: Falta profundidad en X." in result.meta["siege_result"]

            # Verificar llamadas
            assert mock_think.call_count == 2

            # Primera llamada: OMEGA
            args1, kwargs1 = mock_think.call_args_list[0]
            assert kwargs1["mode"] == "omega"

            # Segunda llamada: REFINEMENT
            args2, kwargs2 = mock_think.call_args_list[1]
            assert "INQUISITORIAL CRITIQUE" in args2[0]
            assert kwargs2["mode"] == "deep_reasoning"

            # El inquisidor fue llamado con la hipótesis
            mock_inquisitor.asediar.assert_called_once_with(
                "Hipótesis inicial perfecta.", original_prompt="¿Cómo asegurar la persistencia?"
            )
