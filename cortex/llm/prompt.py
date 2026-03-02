# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX LLM — Sovereign prompt model.

CortexPrompt is the provider-agnostic representation of an LLM instruction.
Independent of OpenAI, Anthropic, Gemini, etc. — the adapter layer lives
in each BaseProvider.invoke() implementation.

Axiom: Ω₂ (Landauer's Razor) — one file, one responsibility.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from cortex.llm._types import IntentProfile


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
    intent: IntentProfile = Field(
        default=IntentProfile.GENERAL,
        description=(
            "Tipo de intención del prompt. Determina qué fallbacks son "
            "elegibles para el cascade determinista. GENERAL usa todos."
        ),
    )

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


__all__ = ["CortexPrompt"]
