# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.0 — Sovereign Immune Boundary.

Frontera determinista (KETER-∞ Phase 1) que garantiza que ninguna
salida malformada de un LLM contamine el estado interno de CORTEX.
Basado en Pydantic v2 Core para validación ultrarrápida (Rust).
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from cortex.utils.errors import CortexError

logger = logging.getLogger("cortex.llm.boundary")

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
    """Barrera estricta de validación para salidas LLM.

    Inyecta un bucle de autoreparación local: si la IA devuelve
    un JSON inválido, se retroalimenta el error en el prompt
    para que la IA lo corrija antes de rendirse.
    """

    @staticmethod
    async def enforce(
        schema: type[T],
        generation_func: Callable[[str | None], Awaitable[str]],
        max_retries: int = 3,
    ) -> T:
        """Fuerza a que el resultado de `generation_func` cumpla el `schema`.

        Args:
            schema: Modelo Pydantic esperado.
            generation_func: Función asíncrona que retorna JSON crudo.
                            Recibe el error de validación anterior (o None).
            max_retries: Intentos antes de emitir un CortexError soberano.

        Returns:
            Instancia validada de `schema`.

        Raises:
            CortexError: Si falla la validación después de `max_retries`.
        """
        last_error_msg: str | None = None
        last_exception: Exception | None = None

        import inspect
        schema_dict = schema.model_json_schema()

        for attempt in range(max_retries):
            try:
                # Determinar cuántos argumentos acepta la función de generación
                # Axioma 14: Determinismo Estructural (DFA schema)
                sig = inspect.signature(generation_func)
                params = len(sig.parameters)

                if params >= 2:
                    raw_output = await generation_func(schema_dict, last_error_msg)
                else:
                    # Por defecto pasamos el schema (Axioma 14)
                    raw_output = await generation_func(schema_dict)

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
                # Si falló por argumentos (TypeError), informamos detalle
                last_error_msg = f"Parsing failure: {str(e)}"
                logger.warning(
                    "ImmuneBoundary: Parsing failure for %s (attempt %d/%d): %s",
                    schema.__name__,
                    attempt + 1,
                    max_retries,
                    str(e),
                )

        logger.error("ImmuneBoundary: Defense compromised after %d attempts.", max_retries)
        raise CortexError(
            f"Falla la inmunidad química: comprometida tras {max_retries} intentos "
            f"validando {schema.__name__}. Error final: {last_exception}"
        )
