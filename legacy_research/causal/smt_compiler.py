import logging
from typing import List, Optional, Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Try to import the compiled PyO3 extension
try:
    import cortex_native
    rust_ext = cortex_native
except ImportError:
    try:
        import cortex_rs
        rust_ext = cortex_rs
    except ImportError:
        logger.warning("Could not import Rust extensions. Causal Compiler will be disabled.")
        rust_ext = None

class PySceneState(BaseModel):
    id: str
    geography_id: Optional[str] = None
    palette_state: str = ""
    emotional_state: Optional[str] = None
    lineage_state: Optional[str] = None

class PyEdgeRule(BaseModel):
    from_id: str
    to_id: str
    rule_type: str  # "HardGeographyLock", "PaletteArcPosition", etc.

class SMTCompiler:
    """
    Causal Compiler Python Bridge.
    Connects to the Z3-backed `cortex_rs.smt_compiler` Rust extension.
    """
    def __init__(self):
        if not rust_ext:
            raise RuntimeError("Rust Causal Compiler module is not available.")
        
        # Load Rust classes
        self.SceneState = getattr(rust_ext, "SceneState", None)
        self.EdgeRule = getattr(rust_ext, "EdgeRule", None)
        self.ContinuityRuleType = getattr(rust_ext, "ContinuityRuleType", None)
        self.GateStatus = getattr(rust_ext, "GateStatus", None)
        self.validate_fn = getattr(rust_ext, "validate_scene_transition", None)
        
        if not all([self.SceneState, self.EdgeRule, self.validate_fn]):
            raise RuntimeError("Incomplete Rust Causal Compiler bindings.")

    def _map_rule_type(self, rule_str: str) -> Any:
        # Maps string to Rust ContinuityRuleType enum
        if rule_str == "HardGeographyLock":
            return self.ContinuityRuleType.HardGeographyLock
        elif rule_str == "PaletteArcPosition":
            return self.ContinuityRuleType.PaletteArcPosition
        elif rule_str == "EmotionalCausality":
            return self.ContinuityRuleType.EmotionalCausality
        elif rule_str == "LineageIntegrity":
            return self.ContinuityRuleType.LineageIntegrity
        else:
            raise ValueError(f"Unknown rule type: {rule_str}")

    def validate_transition(self, from_state: PySceneState, to_state: PySceneState, rules: List[PyEdgeRule]) -> dict:
        """
        Takes Python Pydantic models, converts to Rust structs, and validates via Z3 SMT solver.
        Returns the Verdict as a dictionary.
        """
        # Convert Python models to Rust structs
        rust_from = self.SceneState(
            from_state.id, 
            from_state.geography_id, 
            from_state.palette_state, 
            from_state.emotional_state, 
            from_state.lineage_state
        )
        
        rust_to = self.SceneState(
            to_state.id, 
            to_state.geography_id, 
            to_state.palette_state, 
            to_state.emotional_state, 
            to_state.lineage_state
        )
        
        rust_rules = []
        for r in rules:
            rule_enum = self._map_rule_type(r.rule_type)
            rust_rules.append(self.EdgeRule(r.from_id, r.to_id, rule_enum))

        # Invoke Z3 validation
        verdict = self.validate_fn(rust_from, rust_to, rust_rules)
        
        # Parse output status (which is an enum object)
        status_str = "Unknown"
        if verdict.status == self.GateStatus.Satisfied:
            status_str = "Satisfied"
        elif verdict.status == self.GateStatus.Violated:
            status_str = "Violated"
        elif verdict.status == self.GateStatus.Unspecified:
            status_str = "Unspecified"

        return {
            "status": status_str,
            "proof_trace": verdict.proof_trace,
            "unsat_core": verdict.unsat_core,
            "entropy_hash": verdict.entropy_hash
        }
