"""
NOUS Intent Parser.
Transforms stochastic natural language intent into strict Declarative AST.
Reality Level: C5-REAL
"""

import json
from typing import Any

from pydantic import BaseModel, Field


class MigrationAction(BaseModel):
    action_type: str = Field(
        ..., description="Type of migration action: CREATE_TABLE, ADD_COLUMN, DROP_COLUMN"
    )
    table_name: str = Field(..., description="Target table name")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Parameters for the action"
    )


class MigrationIntent(BaseModel):
    description: str = Field(..., description="Original human intent description")
    actions: list[MigrationAction] = Field(..., description="List of declarative actions (AST)")


class IntentParser:
    """
    Parses LLM output (assumed to be a JSON string matching the schema)
    into a typed declarative plan.
    """

    @staticmethod
    def parse_llm_json(raw_json: str) -> MigrationIntent:
        """
        In a real scenario, this takes the raw output from an LLM.
        We assume the LLM output is strictly JSON.
        """
        try:
            data = json.loads(raw_json)
            return MigrationIntent(**data)
        except Exception as e:  # noqa: BLE001
            raise ValueError(f"Failed to parse stochastic intent into strict AST: {str(e)}")
