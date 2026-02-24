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

logger = logging.getLogger("cortex.llm.boundary")

T = TypeVar("T", bound=BaseModel)


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

        for attempt in range(max_retries):
            try:
                # El LLM genera la respuesta, posiblemente usando el feedback del error anterior
                raw_output = await generation_func(last_error_msg)

                # Limpieza básica de bloques de código Markdown
                clean_output = raw_output.strip()
                if clean_output.startswith("```json"):
                    clean_output = clean_output[7:]
                elif clean_output.startswith("```"):
                    clean_output = clean_output[3:]
                if clean_output.endswith("```"):
                    clean_output = clean_output[:-3]
                clean_output = clean_output.strip()

                return schema.model_validate_json(clean_output)

            except ValidationError as e:
                last_exception = e
                last_error_msg = f"Schema violation: {e.json()}"
                logger.warning(
                    "ImmuneBoundary: Schema violation for %s (attempt %d/%d).",
                    schema.__name__,
                    attempt + 1,
                    max_retries,
                )
            except (ValueError, TypeError) as e:
                last_exception = e
                last_error_msg = f"Parsing failure: {str(e)}"
                logger.warning(
                    "ImmuneBoundary: Parsing failure for %s (attempt %d/%d): %s",
                    schema.__name__,
                    attempt + 1,
                    max_retries,
                    str(e),
                )

        from cortex.utils.errors import CortexError

        logger.error("ImmuneBoundary: Defense compromised after %d attempts.", max_retries)
        raise CortexError(
            f"Immunity compromised after {max_retries} attempts "
            f"validating {schema.__name__}. Final error: {last_exception}"
        )
