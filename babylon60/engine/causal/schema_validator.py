"""L0-L6 Audit Pipeline Schema Validator — C5-REAL Structural Isomorphism."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import jsonschema
from pydantic import ValidationError

from babylon60.engine.causal.pydantic_schemas import ExperimentSchemaL4, PredictionSchemaL3

logger = logging.getLogger(__name__)

# Singleton FormatChecker — instantiating per-call is pure anergy.
_FORMAT_CHECKER = jsonschema.FormatChecker()

# Semantic level → schema stem mapping.
# Callers can use either "L0" or "evidence.schema" interchangeably.
LEVEL_MAP: dict[str, str] = {
    "L0": "evidence.schema",
    "L1": "pattern.schema",
    "L2": "model.schema",
    "L3": "prediction.schema",
    "L4": "experiment.schema",
    "L5": "intervention.schema",
    "L6": "intervention.schema",
}


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Deterministic validation outcome with full error enumeration."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    schema_level: str = ""

    def __bool__(self) -> bool:
        return self.valid


def _resolve_schemas_dir(schemas_dir: str | Path) -> Path:
    """Resolve schema directory: relative to repo root via file hierarchy, then fallback to literal."""
    path = Path(schemas_dir)
    if path.is_absolute() and path.is_dir():
        return path
    # Climb from this file: causal/ -> engine/ -> cortex/ -> repo_root/
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    candidate = repo_root / str(schemas_dir)
    if candidate.is_dir():
        return candidate
    return path


class L0L6SchemaValidator:
    """
    CORTEX-Persist C5-REAL Schema Validator.

    Enforces structural isomorphism of the L0-L6 Audit Pipeline via
    jsonschema Draft-07 with format checking (uuid, date-time) and
    additionalProperties enforcement.
    """

    __slots__ = ("schemas_dir", "_schemas")

    def __init__(self, schemas_dir: str | Path = "schema") -> None:
        self.schemas_dir: Path = _resolve_schemas_dir(schemas_dir)
        self._schemas: dict[str, dict[str, Any]] = {}
        self._load_schemas()

    def _load_schemas(self) -> None:
        """Load and harden all L0-L6 schemas from the filesystem."""
        schema_files = sorted(self.schemas_dir.glob("*.schema.json"))
        if not schema_files:
            raise RuntimeError(
                f"C5-REAL Schema Initialization Failed: no *.schema.json found in {self.schemas_dir}"
            )
        for schema_path in schema_files:
            try:
                with open(schema_path, encoding="utf-8") as f:
                    schema = json.load(f)
                # Enforce additionalProperties: false at root level if not explicitly set.
                # This prevents silent acceptance of garbage keys.
                if "additionalProperties" not in schema:
                    schema["additionalProperties"] = False
                self._schemas[schema_path.stem] = schema
            except (json.JSONDecodeError, OSError) as e:
                raise RuntimeError(
                    f"C5-REAL Schema Load Failed for {schema_path.name}: {e}"
                ) from e
        logger.info(
            "Loaded %d structural schemas for L0-L6 pipeline from %s.",
            len(self._schemas),
            self.schemas_dir,
        )

    @property
    def available_schemas(self) -> list[str]:
        """Return list of loaded schema stems."""
        return list(self._schemas.keys())

    def _resolve_level(self, level: str) -> Optional[str]:
        """Resolve a semantic level (L0-L6) or direct schema stem to a schema key."""
        if level in self._schemas:
            return level
        mapped = LEVEL_MAP.get(level.upper())
        if mapped and mapped in self._schemas:
            return mapped
        return None

    def validate(self, level: str, payload: dict[str, Any]) -> ValidationResult:
        """
        Full validation with complete error enumeration.

        :param level: Schema stem (e.g. 'evidence.schema') or semantic level ('L0').
        :param payload: The dictionary payload to validate.
        :returns: ValidationResult with all detected errors.
        """
        resolved = self._resolve_level(level)
        if resolved is None:
            return ValidationResult(
                valid=False,
                errors=[f"Schema for level '{level}' not found in registry."],
                schema_level=level,
            )

        # Intercept L3 and L4 for Pydantic strict validation
        if resolved == "prediction.schema":
            try:
                PredictionSchemaL3.model_validate(payload)
                return ValidationResult(valid=True, schema_level=resolved)
            except ValidationError as e:
                return ValidationResult(
                    valid=False,
                    errors=[f"[{err['loc']}] {err['msg']}" for err in e.errors()],
                    schema_level=resolved,
                )
        elif resolved == "experiment.schema":
            try:
                ExperimentSchemaL4.model_validate(payload)
                return ValidationResult(valid=True, schema_level=resolved)
            except ValidationError as e:
                return ValidationResult(
                    valid=False,
                    errors=[f"[{err['loc']}] {err['msg']}" for err in e.errors()],
                    schema_level=resolved,
                )

        schema = self._schemas[resolved]
        validator = jsonschema.Draft7Validator(schema, format_checker=_FORMAT_CHECKER)
        errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))

        if not errors:
            return ValidationResult(valid=True, schema_level=resolved)

        error_messages = []
        for err in errors:
            path = ".".join(str(p) for p in err.absolute_path) or "<root>"
            error_messages.append(f"[{path}] {err.message}")

        return ValidationResult(valid=False, errors=error_messages, schema_level=resolved)

    def validate_payload(self, level: str, payload: dict[str, Any]) -> bool:
        """
        Boolean validation — backward-compatible API.

        Logs all errors on failure.
        """
        result = self.validate(level, payload)
        if not result.valid:
            for msg in result.errors:
                logger.error("Validation failed for %s: %s", result.schema_level, msg)
        return result.valid
