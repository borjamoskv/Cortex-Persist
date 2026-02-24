# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.1 — Sovereign LLM Routing (KETER-∞ ROP).

Abstracción arquitectónica para desvincular el motor de razonamiento
de proveedores específicos. Implementa Strategy + Circuit Breaker
con Railway Oriented Programming (Result monads).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence

from pydantic import BaseModel, Field

from cortex.utils.result import Err, Ok, Result

logger = logging.getLogger("cortex.llm.router")


class CortexPrompt(BaseModel):
    """Representación Soberana de una instrucción para el enjambre.
    Independiente del proveedor final (OpenAI, Anthropic, Gemini, etc).
    """

    system_instruction: str = Field(
        default="You are a helpful assistant.",
        description="El prompt del sistema o rol principal.",
    )
    working_memory: list[dict[str, str]] = Field(
        default_factory=list,
        description="Historial reciente o contexto de trabajo (rol/contenido).",
    )
    episodic_context: list[dict[str, str]] | None = Field(
        default=None,
        description="Recuerdos comprimidos o contexto a largo plazo recuperado.",
    )
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0)

    def to_openai_messages(self) -> list[dict[str, str]]:
        """Convierte la estructura soberana al formato de mensajes de OpenAI."""
        messages: list[dict[str, str]] = [{"role": "system", "content": self.system_instruction}]

        # Inyectar contexto episódico si existe, asimilado tempranamente
        if self.episodic_context:
            context_str = "\n".join(
                f"[{m.get('role', 'memory')}]: {m.get('content', '')}"
                for m in self.episodic_context
            )
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"<episodic_context>\n{context_str}\n</episodic_context>\n"
                        "Use this context for the following interactions if relevant."
                    ),
                }
            )

        messages.extend(self.working_memory)
        return messages


class BaseProvider(ABC):
    """Interfaz estricta que todo proveedor LLM debe cumplir."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Identificador único del proveedor."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Nombre del modelo subyacente."""
        pass

    @abstractmethod
    async def invoke(self, prompt: CortexPrompt) -> str:
        """Traduce el CortexPrompt al formato nativo del LLM y ejecuta la inferencia."""
        pass


class CortexLLMRouter:
    """Enrutador resiliente usando Strategy + Circuit Breaker + ROP.

    Retorna Result[str, str] en lugar de lanzar excepciones,
    permitiendo flujo determinista en el enjambre.
    """

    def __init__(self, primary: BaseProvider, fallbacks: Sequence[BaseProvider] | None = None):
        self._primary = primary
        self._fallbacks = list(fallbacks) if fallbacks else []

    @property
    def primary(self) -> BaseProvider:
        return self._primary

    @property
    def fallbacks(self) -> list[BaseProvider]:
        return self._fallbacks

    async def execute_resilient(self, prompt: CortexPrompt) -> Result[str, str]:
        """Ejecuta inferencia con cascade resiliente. Retorna Result.

        Ok(response) en éxito, Err(detail) si todos los proveedores fallan.
        """
        errors: list[str] = []

        # Intento con el primario
        result = await self._try_provider(self._primary, prompt)
        if isinstance(result, Ok):
            return result
        errors.append(f"{self._primary.provider_name}: {result.error}")

        # Cascade a fallbacks
        for fallback in self._fallbacks:
            result = await self._try_provider(fallback, prompt)
            if isinstance(result, Ok):
                return result
            errors.append(f"{fallback.provider_name}: {result.error}")

        # Singularidad Negativa: todos fallaron
        detail = " | ".join(errors)
        logger.error("Singularidad Negativa: %s", detail)
        return Err(f"All providers failed: {detail}")

    async def _try_provider(self, provider: BaseProvider, prompt: CortexPrompt) -> Result[str, str]:
        """Try a single provider, returning Result."""
        try:
            response = await provider.invoke(prompt)
            return Ok(response)
        except Exception as e:  # deliberate boundary — LLM providers can raise any type
            logger.warning("Provider '%s' failed: %s", provider.provider_name, e)
            return Err(str(e))

    async def invoke(self, prompt: CortexPrompt) -> Result[str, str]:
        """Primary entry point — alias for execute_resilient."""
        return await self.execute_resilient(prompt)
