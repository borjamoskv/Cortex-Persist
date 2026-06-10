# [C5-REAL] Exergy-Maximized
"""NOUS Compiler V2 - Declarative AST Compiler via LLM structured output

Reality Level: C5-REAL
"""

from typing import Optional

import instructor
import pydantic
from openai import AsyncOpenAI


class NousInvariant(pydantic.BaseModel):
    name: str
    condition: str
    action: str = "halt"


class NousOperation(pydantic.BaseModel):
    type: str  # e.g., "create_table", "add_column", "drop_table"
    target: str
    sql: str
    rollback_sql: Optional[str] = None


class NousMetadata(pydantic.BaseModel):
    version: str
    author: str
    description: str
    requires_lock: bool = True


class NousAST(pydantic.BaseModel):
    metadata: NousMetadata
    ensures: list[str]
    operations: list[NousOperation]
    invariants: list[NousInvariant]


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
