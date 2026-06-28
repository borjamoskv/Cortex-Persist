import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ApexPrimitive:
    id: str
    name: str
    execute: str
    trigger: str
    verify: str
    fail: str


@dataclass(frozen=True)
class OuroborosInvariant:
    id: str
    name: str
    rule: str


class ApexRegistry:
    """
    C5-REAL: Registry for MOSKV-1 APEX Primitives & Ouroboros Laws.
    Loads and serves the 100 Sovereign APEX Primitives and 100 Invariants.
    """

    def __init__(self) -> None:
        self._primitives: dict[str, ApexPrimitive] = {}
        self._invariants: dict[str, OuroborosInvariant] = {}
        self._load_registry()

    def _load_registry(self) -> None:
        registry_path = Path(__file__).parent / "APEX_REGISTRY.json"
        if not registry_path.exists():
            return

        with open(registry_path, encoding="utf-8") as f:
            data = json.load(f)

            # Load Primitives
            for p in data.get("primitives", []):
                prim = ApexPrimitive(
                    id=p.get("id", ""),
                    name=p.get("name", ""),
                    execute=p.get("execute", ""),
                    trigger=p.get("trigger", ""),
                    verify=p.get("verify", ""),
                    fail=p.get("fail", ""),
                )
                self._primitives[prim.id] = prim

            # Load Invariants
            for inv in data.get("invariants", []):
                invariant = OuroborosInvariant(
                    id=inv.get("id", ""), name=inv.get("name", ""), rule=inv.get("rule", "")
                )
                self._invariants[invariant.id] = invariant

    def get_primitive(self, apex_id: str) -> Optional[ApexPrimitive]:
        """Retrieve a specific primitive by ID (e.g. 'APEX-001')"""
        return self._primitives.get(apex_id)

    def list_primitives(self) -> list[ApexPrimitive]:
        """List all loaded primitives"""
        return list(self._primitives.values())

    def get_invariant(self, inv_id: str) -> Optional[OuroborosInvariant]:
        """Retrieve a specific invariant by ID (e.g. 'OUROBOROS-001')"""
        return self._invariants.get(inv_id)

    def list_invariants(self) -> list[OuroborosInvariant]:
        """List all loaded invariants"""
        return list(self._invariants.values())


# Singleton instance
apex_registry = ApexRegistry()
