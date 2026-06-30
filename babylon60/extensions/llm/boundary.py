# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""Sovereign Immune Boundary.

Deterministic boundary (KETER-∞ Phase 1) that ensures no
malformed LLM output contaminates the internal state of CORTEX.
Based on Pydantic v2 Core for ultra-fast validation (Rust).
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from babylon60.utils.errors import CortexError
from pydantic import BaseModel, ValidationError

logger = logging.getLogger("cortex_extensions.llm.boundary")

T = TypeVar("T", bound=BaseModel)


# Maximum characters of error detail to feed back to the LLM.
# Avoids wasting tokens on a 2KB Pydantic dump.
_MAX_ERROR_FEEDBACK = 500


def _clean_llm_json(raw: str) -> str:
    """Extract pure JSON from LLM output that may include prose/markdown.

    Handles common patterns:
    - ```json\n{...}\n```
    - "Here is the JSON:\n```json\n{...}```"
    - Raw JSON with leading/trailing whitespace
    - JSON with BOM or invisible chars
    """
    clean = raw.strip()

    # Strip markdown fences
    if "```json" in clean:
        start = clean.index("```json") + 7
        end = clean.find("```", start)
        clean = clean[start:end] if end > start else clean[start:]
    elif "```" in clean:
        start = clean.index("```") + 3
        end = clean.find("```", start)
        clean = clean[start:end] if end > start else clean[start:]

    clean = clean.strip()

    # If still not starting with { or [, hunt for first JSON-like char
    if clean and clean[0] not in ("{", "["):
        for i, ch in enumerate(clean):
            if ch in ("{", "["):
                clean = clean[i:]
                break

    return clean


class ImmuneBoundary:
    """Strict validation barrier for LLM outputs.

    Injects a local auto-repair loop: if the AI returns
    an invalid JSON, the error is fed back into the prompt
    so the AI can correct it before giving up.
    """

    @staticmethod
    async def enforce(
        schema: type[T],
        generation_func: Callable[[str | None], Awaitable[str]],
        max_retries: int = 3,
    ) -> T:
        """Forces the result of `generation_func` to comply with the `schema`.

        Args:
            schema: Expected Pydantic model.
            generation_func: Async function returning raw JSON.
                            Receives the previous validation error (or None).
            max_retries: Attempts before emitting a sovereign CortexError.

        Returns:
            Validated instance of `schema`.

        Raises:
            CortexError: If validation fails after `max_retries`.
        """
        last_error_msg: str | None = None
        last_exception: Exception | None = None

        import inspect

        schema_dict = schema.model_json_schema()

        schema_dict = schema.model_json_schema()

        for attempt in range(max_retries):
            try:
                # Determine how many arguments the generation function accepts
                # Axiom 14: Structural Determinism (DFA schema)
                sig = inspect.signature(generation_func)
                params = len(sig.parameters)

                if params >= 2:
                    raw_output = await generation_func(schema_dict, last_error_msg)  # type: ignore[reportCallIssue]
                else:
                    # By default we pass the schema (Axiom 14)
                    raw_output = await generation_func(schema_dict)  # type: ignore[type-error]

                clean_output = _clean_llm_json(raw_output)
                return schema.model_validate_json(clean_output)

            except ValidationError as e:
                last_exception = e
                err_detail = e.json()[:_MAX_ERROR_FEEDBACK]
                last_error_msg = f"Schema violation: {err_detail}"
                logger.warning(
                    "ImmuneBoundary: Schema violation for %s (attempt %d/%d).",
                    schema.__name__,
                    attempt + 1,
                    max_retries,
                )
            except (ValueError, TypeError) as e:
                last_exception = e
                # If it failed due to arguments (TypeError), provide detail
                last_error_msg = f"Parsing failure: {e!s}"
                logger.warning(
                    "ImmuneBoundary: Parsing failure for %s (attempt %d/%d): %s",
                    schema.__name__,
                    attempt + 1,
                    max_retries,
                    str(e),
                )

        logger.error("ImmuneBoundary: Defense compromised after %d attempts.", max_retries)
        raise CortexError(
            f"Chemical immunity failure: compromised after {max_retries} attempts "
            f"validating {schema.__name__}. Final error: {last_exception}"
        )
