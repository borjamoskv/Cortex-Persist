# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v6 — Schema Theory (Top-Down Memory Processing).

Based on Bartlett (1932): Memory is guided by pre-existing schemas.
Schemas act as attentional filters (encoding) and retrieval guides,
preventing the indiscriminate logging of raw text and increasing
relevance during fetch.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic import BaseModel, Field

logger = logging.getLogger("cortex.memory.schemas")

__all__ = ["MemorySchema", "SchemaEngine", "SchemaEngineConfig"]


class MemorySchema(BaseModel):
    """
    A cognitive schema representing a typical situation or pattern.
    """

    name: str = Field(description="Unique name for the schema, e.g., 'error_debugging'.")
    description: str = Field(description="Human-readable description of the schema.")
    triggers: list[str] = Field(
        default_factory=list, description="Keywords/patterns that activate this schema."
    )
    encoding_focus: list[str] = Field(
        default_factory=list, description="Concepts to prioritize during encoding."
    )
    encoding_ignore: list[str] = Field(
        default_factory=list, description="Concepts to drop (reduces entropy)."
    )
    retrieval_bias: list[str] = Field(
        default_factory=list, description="Concepts to inject into search queries."
    )
    expected_structure: dict[str, str] = Field(
        default_factory=dict, description="Optional key-value expected structure."
    )


@dataclass()
class SchemaEngineConfig:
    enabled: bool = True
    match_threshold: float = 0.5  # Unused if simple keyword match


class SchemaEngine:
    """
    Applies Schema Theory top-down processing to memory operations.
    """

    __slots__ = ("_schemas", "_config")

    def __init__(
        self, schemas: list[MemorySchema] | None = None, config: SchemaEngineConfig | None = None
    ) -> None:
        self._config = config or SchemaEngineConfig()
        self._schemas: dict[str, MemorySchema] = {}
        if schemas:
            for s in schemas:
                self._schemas[s.name] = s

        # Register default internal schemas if none provided
        if not self._schemas:
            self._register_default_schemas()

    def _register_default_schemas(self) -> None:
        """Register basic ubiquitous schemas for CORTEX."""
        debug_schema = MemorySchema(
            name="error_debugging",
            description="Schema activated when investigating stacktraces or bugs.",
            triggers=[
                "error:",
                "exception",
                "traceback",
                "bug",
                "crash",
                "traceback (most recent call last)",
            ],
            encoding_focus=["Stacktrace", "Cause", "Resolution", "Fix", "File Path"],
            encoding_ignore=["Frustration", "Complaints", "Greetings", "Thanks"],
            retrieval_bias=["error resolution", "bug fix", "stacktrace analysis"],
        )
        ml_schema = MemorySchema(
            name="machine_learning",
            description="Schema for AI/ML specific tasks.",
            triggers=[
                "model",
                "training",
                "loss",
                "epochs",
                "dataset",
                "inference",
                "pytorch",
                "tensorflow",
            ],
            encoding_focus=["Architecture", "Hyperparameters", "Metrics", "Loss Evolution"],
            encoding_ignore=["Setup logs", "Progress bars", "Warnings"],
            retrieval_bias=["model architecture", "training loop", "dataset prep", "evaluation"],
        )
        front_schema = MemorySchema(
            name="frontend_ui",
            description="Schema for UI/UX Frontend operations.",
            triggers=["css", "tailwind", "ui", "component", "react", "html", "viewport"],
            encoding_focus=["Component State", "Styling Tokens", "Accessibility", "Animations"],
            encoding_ignore=["Server logs", "Database IDs"],
            retrieval_bias=["ui component", "styling", "frontend state"],
        )

        for s in (debug_schema, ml_schema, front_schema):
            self._schemas[s.name] = s

    def match_schema(self, text: str) -> MemorySchema | None:
        """
        Identify the most relevant schema for the given context text using fast triggers.
        Returns first match or None. O(S*T) purely in memory.
        """
        if not self._config.enabled or not text:
            return None

        lower_text = text.lower()
        for schema in self._schemas.values():
            for trigger in schema.triggers:
                if trigger.lower() in lower_text:
                    logger.debug("Schema '%s' triggered by keyword '%s'", schema.name, trigger)
                    return schema
        return None

    def apply_encoding_schema(self, schema: MemorySchema, content: str) -> str:
        """
        Top-Down Filtering: Shapes the string to encode by highlighting the focus.
        (Future integration: Use local LLM to structurally conform the text).
        """
        if not self._config.enabled:
            return content

        focus_tags = ", ".join(schema.encoding_focus)
        schema_header = f"[SCHEMA: {schema.name} | FOCUS: {focus_tags}]\n"

        # Simplistic noise reduction: Strip common ignore-words if entire lines match.
        filtered_lines = []
        for line in content.splitlines():
            lower_line = line.lower()
            should_ignore = False
            for ignore in schema.encoding_ignore:
                # Basic heuristic to avoid dropping code lines accidentally
                # Only drop if the line is very short and matches the ignore term
                if ignore.lower() in lower_line and len(line) < 50:
                    should_ignore = True
                    break
            if not should_ignore:
                filtered_lines.append(line)

        return f"{schema_header}" + "\n".join(filtered_lines)

    def apply_retrieval_schema(self, schema: MemorySchema, query: str) -> str:
        """
        Top-Down Augmentation: Modifies a search query to include schema biases.
        """
        if not self._config.enabled or not schema.retrieval_bias:
            return query

        bias_str = " ".join(schema.retrieval_bias)
        return f"{query} {bias_str}"

    def add_schema(self, schema: MemorySchema) -> None:
        """Add or overwrite a schema dynamically."""
        self._schemas[schema.name] = schema
