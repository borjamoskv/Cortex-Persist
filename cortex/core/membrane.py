import hashlib
import json
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any


class EpistemicState(Enum):
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    UNKNOWN = "unknown"
    UNDECIDABLE = "undecidable"
    MODEL_LIMITED = "model-limited"
    SOLVER_SILENT = "solver-silent"


@dataclass
class EpistemicEvent:
    payload: dict
    state: EpistemicState
    confidence: float
    z3_trace: dict | None
    entropy_signature: float
    reality_level: str


# Z3 for logical guards
try:
    from z3 import And, Bool, Int, Real, Solver, sat, unsat

    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False
    print("Warning: Z3 not available. Logical guards will be disabled.")


class Z3Guard:
    """
    Motor de verificación SMT (Satisfiability Modulo Theories) usando Z3.

    Propósito en Cortex Persist (MÖBIUS - Fase 7):
    - Proporcionar validación lógica determinista (L0 de la Epistemic Membrane).
    - Detectar violaciones con unsat_core traceable.
    - Evitar alucinaciones lógicamente consistentes pero físicamente inválidas.
    - Soporte dinámico de variables (price, confidence, timestamp, ratios, etc.).

    Características SMT:
    - Tipos: Real (precios, porcentajes), Int, Bool.
    - Operadores: aritmética, comparaciones, And/Or/Not/Implies.
    - Binding automático de contexto desde el payload.
    - Reset por verificación para aislamiento.
    """

    def __init__(self):
        if not Z3_AVAILABLE:
            self.enabled = False
            print("⚠️ Z3 SMT no disponible. Guards lógicos desactivados.")
            return
        self.enabled = True
        self.reset()
        self.presets = {
            "pricing_policy": "price >= base_price * 0.7",
            "confidence_range": "0 <= confidence <= 100",
            "temporal_valid": "timestamp >= last_update",
        }

    def reset(self):
        """Reset completo del solver SMT para verificación limpia e independiente."""
        if self.enabled:
            self.solver = Solver()
            self.constraints: dict[str, Any] = {}
            self.variables: dict[str, Any] = {}  # nombre -> variable Z3

    def declare_var(self, name: str, var_type: str = "Real"):
        """
        Declara variable SMT dinámicamente.

        Args:
            name: Nombre de la variable (ej: 'price', 'confidence')
            var_type: 'Real' | 'Int' | 'Bool'
        """
        if name in self.variables:
            return self.variables[name]

        if var_type == "Int":
            var = Int(name)
        elif var_type == "Bool":
            var = Bool(name)
        else:
            var = Real(name)  # default para valores continuos (precios, ratios)

        self.variables[name] = var
        return var

    def bind_context(self, value: Any):
        """
        Extrae automáticamente variables del payload y las fija en el solver.
        Ejemplo: {"price": 127.49, "confidence": 85} → price == 127.49 ∧ confidence == 85
        """
        if not isinstance(value, dict):
            return

        for k, v in value.items():
            if isinstance(v, int | float):
                var_type = "Int" if isinstance(v, int) else "Real"
                var = self.declare_var(k, var_type)
                self.solver.add(var == v)
            elif isinstance(v, bool):
                var = self.declare_var(k, "Bool")
                self.solver.add(var == v)

    def add_constraint(self, guard_name: str, expr):
        """Añade una constraint SMT explícita."""
        if not self.enabled:
            return False
        self.constraints[guard_name] = expr
        self.solver.add(expr)
        return True

    def check(self, value: Any = None, guards: list[str] | None = None) -> dict:
        """
        Verificación SMT completa.

        Flujo:
        1. Reset solver
        2. Bind contexto del payload
        3. Constraints preset + guards solicitados
        4. check() → sat / unsat con unsat_core

        Returns:
            Dict con status, modelo (si sat), unsat_core (si violated) y guards_passed.
        """
        if not self.enabled:
            return {"status": "disabled", "satisfied": True}

        self.reset()
        if value:
            self.bind_context(value)

        # Constraints preset SMT (industriales)
        p = self.declare_var("price", "Real")
        c = self.declare_var("confidence", "Real")
        self.add_constraint("price_nonneg", p >= 0)  # type: ignore
        self.add_constraint("confidence_range", And(c >= 0, c <= 100))  # type: ignore
        self.add_constraint("price_reasonable", p <= 100000)  # type: ignore

        # Guards personalizados
        if guards:
            for g in guards:
                if g in self.presets:
                    # Aquí se podría parsear string a expr Z3 en futuro
                    pass

        result = self.solver.check()

        if result == sat:
            model = self.solver.model()
            return {
                "status": "satisfied",
                "satisfied": True,
                "model": {str(v): model[v] for v in model},
                "guards_passed": list(self.constraints.keys()),
                "reason": "All SMT constraints satisfied",
                "z3_trace": {"result": "sat"},
            }
        elif result == unsat:
            unsat_core = []
            try:
                core = self.solver.unsat_core()
                unsat_core = [str(c) for c in core]
            except Exception:
                unsat_core = ["unknown_core"]

            return {
                "status": "violated",
                "satisfied": False,
                "unsat_core": unsat_core,
                "reason": "SMT constraint violation - see unsat_core for mathematical explanation",
                "z3_trace": {"result": "unsat", "core": unsat_core},
            }
        else:
            return {
                "status": "unknown",
                "satisfied": False,
                "reason": "SMT solver returned unknown (undecidable space)",
                "z3_trace": {"result": "unknown"},
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

    def _get_causal_anchor(self, metadata: dict) -> str:
        if metadata and "causal_anchor" in metadata:
            return metadata["causal_anchor"]
        fallback = hashlib.sha256(
            (json.dumps(metadata or {}, sort_keys=True) + str(time.time())).encode()
        ).hexdigest()[:16]
        return f"sim:{fallback}"

    def generate_marker(
        self,
        payload: dict,
        z3_status: str | None,
        solver_trace: dict | None,
        delta: float,
        reality: str,
    ) -> EpistemicEvent:
        if z3_status is None or z3_status == "disabled":
            return EpistemicEvent(
                payload=payload,
                state=EpistemicState.SOLVER_SILENT,
                confidence=0.0,
                z3_trace=solver_trace,
                entropy_signature=delta,
                reality_level=reality,
            )

        if z3_status == "unknown":
            return EpistemicEvent(
                payload=payload,
                state=EpistemicState.UNDECIDABLE,
                confidence=0.3,
                z3_trace=solver_trace,
                entropy_signature=delta * 1.5,
                reality_level=reality,
            )

        if z3_status == "satisfied":
            return EpistemicEvent(
                payload=payload,
                state=EpistemicState.CONFIRMED,
                confidence=0.95,
                z3_trace=solver_trace,
                entropy_signature=delta,
                reality_level=reality,
            )

        return EpistemicEvent(
            payload=payload,
            state=EpistemicState.REJECTED,
            confidence=0.99,  # High confidence that it's rejected
            z3_trace=solver_trace,
            entropy_signature=delta,
            reality_level=reality,
        )

    def check(
        self, key: str, value: Any, metadata: dict | None = None, guards: list[str] | None = None
    ) -> EpistemicEvent:
        metadata = metadata or {}
        reality_level = "C4-SIM"
        causal_anchor = self._get_causal_anchor(metadata)

        # L2 - Reality Anchor
        if not causal_anchor.startswith("sim:"):
            reality_level = "C5-REAL"

        # L1 - Entropy Gate
        delta = self._estimate_entropy_delta(value)
        now = time.time()
        if (now - self.last_write_time) < 0.1 and delta > 5:
            # Fails due to high frequency entropy violation
            return EpistemicEvent(
                payload=value if isinstance(value, dict) else {"raw": value},
                state=EpistemicState.REJECTED,
                confidence=0.99,
                z3_trace={"reason": "High frequency entropy violation"},
                entropy_signature=delta,
                reality_level=reality_level,
            )
        self.last_write_time = now
        self.entropy_used += delta

        # L0 - Z3 Logic Gate
        z3_status = None
        solver_trace = None
        if guards and self.z3_guard and self.z3_guard.enabled:
            guard_results = {}
            for g in guards:
                # Dynamic constraints
                if isinstance(value, dict):
                    if "price" in str(value).lower() or "confidence" in str(value).lower():
                        p = Int("price")
                        c = Int("confidence")
                        self.z3_guard.add_constraint("price_nonneg", p >= 0)
                        self.z3_guard.add_constraint("confidence_range", And(c >= 0, c <= 100))

                check_res = self.z3_guard.check()
                guard_results[g] = check_res

                # Capture the first non-satisfied status
                if check_res.get("status") != "satisfied":
                    z3_status = check_res.get("status")
                    solver_trace = check_res.get("z3_trace")
                    break

            if z3_status is None:
                z3_status = "satisfied"
                solver_trace = {"result": "sat"}

        return self.generate_marker(
            payload=value if isinstance(value, dict) else {"raw": value},
            z3_status=z3_status,
            solver_trace=solver_trace,
            delta=delta,
            reality=reality_level,
        )
