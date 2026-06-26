import json
from pathlib import Path
from typing import Dict, List, Any

class ApexRegistry:
    """
    C5-REAL: Registry for MOSKV-1 APEX Primitives.
    Loads and serves the 100 Sovereign APEX Primitives.
    """
    def __init__(self):
        self._primitives: Dict[str, Dict[str, Any]] = {}
        self._load_registry()
        
    def _load_registry(self):
        registry_path = Path(__file__).parent / "APEX_REGISTRY.json"
        if not registry_path.exists():
            return
            
        with open(registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for p in data.get("primitives", []):
                self._primitives[p["id"]] = p

    def get_primitive(self, apex_id: str) -> Dict[str, Any]:
        """Retrieve a specific primitive by ID (e.g. 'APEX-001')"""
        return self._primitives.get(apex_id)

    def list_all(self) -> List[Dict[str, Any]]:
        """List all loaded primitives"""
        return list(self._primitives.values())

# Singleton instance
apex_registry = ApexRegistry()
