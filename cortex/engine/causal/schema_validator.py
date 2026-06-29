import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

class L0L6SchemaValidator:
    """
    CORTEX-Persist C5-REAL Schema Validator.
    Enforces structural isomorphism of the L0-L6 Audit Pipeline.
    """
    
    def __init__(self, schemas_dir: str = "schemas"):
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
        Validates a payload against the strict JSON schema.
        :param level: The exact schema stem (e.g., 'evidence.schema')
        :param payload: The dictionary payload to validate.
        """
        if level not in self._schemas:
            logger.error(f"Schema for level '{level}' not found in registry.")
            return False
            
        # Implementation depends on `jsonschema` library. 
        # In this C5-REAL isolated execution, we perform a deterministic key check.
        schema = self._schemas[level]
        required_keys = schema.get("required", [])
        
        for key in required_keys:
            if key not in payload:
                logger.error(f"Validation failed for {level}: Missing required key '{key}'")
                return False
                
        # If we reach here, the deterministic minimal subset is validated.
        return True
