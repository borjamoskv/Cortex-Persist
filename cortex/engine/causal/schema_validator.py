import json
import logging
from pathlib import Path
from typing import Any, Dict
import jsonschema

logger = logging.getLogger(__name__)

class L0L6SchemaValidator:
    """
    CORTEX-Persist C5-REAL Schema Validator.
    Enforces structural isomorphism of the L0-L6 Audit Pipeline.
    """
    
    def __init__(self, schemas_dir: str = "schema"):
        if schemas_dir == "schema":
            # Dynamic lookup relative to this file to prevent CWD dependency
            possible_path = Path(__file__).resolve().parent.parent.parent.parent / "schema"
            if possible_path.exists() and possible_path.is_dir():
                self.schemas_dir = possible_path
            else:
                self.schemas_dir = Path(schemas_dir)
        else:
            self.schemas_dir = Path(schemas_dir)

        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._load_schemas()
        
    def _load_schemas(self) -> None:
        """Loads all L0-L6 schemas from the filesystem."""
        try:
            for schema_path in self.schemas_dir.glob("*.schema.json"):
                with open(schema_path, "r", encoding="utf-8") as f:
                    self._schemas[schema_path.stem] = json.load(f)
            logger.info(f"Loaded {len(self._schemas)} structural schemas for L0-L6 pipeline.")
        except Exception as e:
            # Catching generic exception during init as per C5-REAL boundary constraints
            logger.error(f"Failed to load schemas: {e}")
            raise RuntimeError(f"C5-REAL Schema Initialization Failed: {e}") from e

    def validate_payload(self, level: str, payload: Dict[str, Any]) -> bool:
        """
        Validates a payload against the strict JSON schema using the jsonschema library.
        :param level: The exact schema stem (e.g., 'evidence.schema')
        :param payload: The dictionary payload to validate.
        """
        if level not in self._schemas:
            logger.error(f"Schema for level '{level}' not found in registry.")
            return False
            
        schema = self._schemas[level]
        try:
            jsonschema.validate(instance=payload, schema=schema, format_checker=jsonschema.FormatChecker())
            return True
        except jsonschema.ValidationError as e:
            logger.error(f"Validation failed for {level}: {e.message}")
            return False
        except jsonschema.SchemaError as e:
            logger.error(f"Invalid schema definition for {level}: {e.message}")
            return False

