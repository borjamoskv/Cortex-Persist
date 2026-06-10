# [C5-REAL] Exergy-Maximized
"""NOUS Compiler V2 - Declarative AST Compiler via LLM structured output

Reality Level: C5-REAL
"""

import instructor
from openai import AsyncOpenAI

from cortex.extensions.nous.models import NousAST


class NousCompilerV2:
    def __init__(self, client: AsyncOpenAI = None):
        if client is None:
            client = AsyncOpenAI()
        self.client = instructor.from_openai(client)

    async def compile(self, manifest_text: str) -> NousAST:
        """Compiles a raw .nous manifest text into a typed NousAST using LLM."""
        return await self.client.chat.completions.create(
            model="gpt-4o",
            response_model=NousAST,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict database compiler. Your job is to parse a raw declarative "
                        "migration manifest (.nous format) and convert it exactly into the NousAST structure. "
                        "Extract the metadata, ensure conditions, specific SQL operations with their rollback "
                        "equivalents, and any invariants."
                    ),
                },
                {"role": "user", "content": manifest_text},
            ],
            temperature=0.0,
        )
