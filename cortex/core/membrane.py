import json
import hashlib
import time
from typing import Any, Dict, List

# Z3 for logical guards
try:
    from z3 import Solver, Int, Bool, And, sat, unsat
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False
    print("Warning: Z3 not available. Logical guards will be disabled.")

class Z3Guard:
    """Z3 SMT Solver avanzado para verificación lógica en la Epistemic Membrane"""
    
    def __init__(self):
        if not Z3_AVAILABLE:
            self.enabled = False
            return
        self.enabled = True
        self.reset()

    def reset(self):
        """Reset solver para verificación limpia"""
        if self.enabled:
            self.solver = Solver()
            self.constraints = {}
            self.variables = {}  # name -> Z3 var

    def declare_var(self, name: str, var_type="Real"):
        """Declara variables SMT dinámicamente"""
        if name in self.variables:
            return self.variables[name]
        
        if var_type == "Int":
            var = Int(name)
        elif var_type == "Bool":
            var = Bool(name)
        else:  # default Real para precios, ratios, etc.
            var = Real(name)
        
        self.variables[name] = var
        return var

    def add_constraint(self, guard_name: str, expr):
        """Añadir constraint SMT"""
        if not self.enabled:
            return False
        self.constraints[guard_name] = expr
        self.solver.add(expr)
        return True

    def bind_context(self, value: Any):
        """Extrae variables del payload y las declara en el solver"""
        if not isinstance(value, dict):
            return
        
        for k, v in value.items():
            if isinstance(v, (int, float)):
                var = self.declare_var(k, "Real" if isinstance(v, float) else "Int")
                # Añadir constraint de igualdad para este write
                self.solver.add(var == v)
            elif isinstance(v, bool):
                var = self.declare_var(k, "Bool")
                self.solver.add(var == v)

    def check(self, value: Any = None, guards: List[str] = None) -> Dict:
        """Verificación SMT completa"""
        if not self.enabled:
            return {"status": "disabled", "satisfied": True}
        
        self.reset()  # Clean state per check
        
        if value:
            self.bind_context(value)
        
        # Presets SMT comunes
        p = self.declare_var("price", "Real")
        c = self.declare_var("confidence", "Real")
        
        self.add_constraint("price_nonneg", p >= 0)
        self.add_constraint("confidence_range", And(c >= 0, c <= 100))
        self.add_constraint("price_reasonable", p <= 10000)  # ejemplo industrial
        
        if guards:
            for g in guards:
                # Aquí se pueden registrar guards custom por nombre
                pass
        
        result = self.solver.check()
        
        if result == sat:
            model = self.solver.model()
            return {
                "status": "satisfied",
                "satisfied": True,
                "model": {str(v): model[v] for v in model if str(v) in ["price", "confidence"]},
                "guards_passed": list(self.constraints.keys())
            }
        else:
            unsat_core = []
            try:
                core = self.solver.unsat_core()
                unsat_core = [str(c) for c in core]
            except:
                unsat_core = ["unknown"]
            
            return {
                "status": "violated",
                "satisfied": False,
                "unsat_core": unsat_core,
                "reason": "Constraint violation detected by Z3 SMT solver"
            }


class EpistemicMembrane:
    """
    Interceptor obligatorio (Fase 6 - MÖBIUS):
    L0: Z3 Logic Gate
    L1: Entropy Gate (fricción termodinámica)
    L2: Reality Anchor (C5-REAL enforcer)
    """
    def __init__(self, z3_guard: Z3Guard):
        self.z3_guard = z3_guard
        self.last_write_time = time.time()
        self.token_budget = 1000
        self.entropy_used = 0

    def _estimate_entropy_delta(self, value: Any) -> float:
        payload_str = json.dumps(value, ensure_ascii=False)
        return len(payload_str) / 100.0

    def _get_causal_anchor(self, metadata: Dict) -> str:
        if metadata and "causal_anchor" in metadata:
            return metadata["causal_anchor"]
        fallback = hashlib.sha256(
            (json.dumps(metadata or {}, sort_keys=True) + str(time.time())).encode()
        ).hexdigest()[:16]
        return f"sim:{fallback}"

    def check(self, key: str, value: Any, metadata: Dict = None, guards: List[str] = None) -> Dict:
        metadata = metadata or {}
        result = {
            "reality_level": "C4-SIM",
            "z3_validation": {},
            "entropy_delta": 0.0,
            "causal_anchor": self._get_causal_anchor(metadata),
            "passed": True,
            "reasons": []
        }

        # L0 - Z3 Logic Gate
        if guards and self.z3_guard and self.z3_guard.enabled:
            guard_results = {}
            for g in guards:
                # Dynamic constraints
                if isinstance(value, dict):
                    if "price" in str(value).lower() or "confidence" in str(value).lower():
                        p = Int('price')
                        c = Int('confidence')
                        self.z3_guard.add_constraint("price_nonneg", p >= 0)
                        self.z3_guard.add_constraint("confidence_range", And(c >= 0, c <= 100))
                guard_results[g] = self.z3_guard.check()
            result["z3_validation"] = guard_results
            if any(not g.get("satisfied", True) for g in guard_results.values()):
                result["passed"] = False
                result["reasons"].append("Z3 constraint violation")
                return result

        # L1 - Entropy Gate
        delta = self._estimate_entropy_delta(value)
        result["entropy_delta"] = delta
        now = time.time()
        if (now - self.last_write_time) < 0.1 and delta > 5:
            result["passed"] = False
            result["reasons"].append("High frequency entropy violation")
        self.last_write_time = now
        self.entropy_used += delta

        # L2 - Reality Anchor
        if not result["causal_anchor"].startswith("sim:"):
            result["reality_level"] = "C5-REAL"
        else:
            result["reasons"].append("No causal proof → C4-SIM")

        if result["passed"]:
            result["reasons"].append("Membrane passed")

        return result
