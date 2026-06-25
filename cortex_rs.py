# [C5-REAL] Exergy-Maximized
"""
cortex_rs.py
Strict Native Bridge to cortex_core_rs.
C4-SIM is strictly prohibited. If Rust bindings fail to load, the system hard-fails.
"""


from cortex_core_rs import (
    ASTProjector,
    CognitiveState,
    ExergyRouter,
    Fixed60,
    MTKAuthorizer,
    RetrievalGraph,
    RetrievalNode,
    authorize_sqlite_mutation,
    batch_merkle_root,
    compute_friston_penalty,
    execute_mee_transfer,
    generate_evidence_hash,
    hash_ast,
    ingest_reality_claim,
    init_c5_gate_1_schema,
    log_ast_check,
    validate_exergy_mutation,
    validate_metric_json,
    verify_causal_assertion,
    verify_ephemeral_token,
    mint_ephemeral_token,
    causal_distance,
    hash_distance_rollup,
)
from cortex_core_rs import (
    calculate_entropy_b60 as _calc_entropy_rust,
)

__all__ = [
    "ASTProjector",
    "CognitiveState",
    "ExergyRouter",
    "Fixed60",
    "MTKAuthorizer",
    "RetrievalGraph",
    "RetrievalNode",
    "authorize_sqlite_mutation",
    "batch_merkle_root",
    "compute_friston_penalty",
    "execute_mee_transfer",
    "generate_evidence_hash",
    "hash_ast",
    "ingest_reality_claim",
    "init_c5_gate_1_schema",
    "log_ast_check",
    "validate_exergy_mutation",
    "validate_metric_json",
    "verify_causal_assertion",
    "verify_ephemeral_token",
    "mint_ephemeral_token",
    "causal_distance",
    "hash_distance_rollup",
    "calculate_entropy_b60",
    "Babylon60",
]


# Keep the Python wrapper for Cortex/Babylon60 to provide Pythonic dunder methods
# utilizing the rust backend for pure entropy math
class Cortex:
    def __init__(self, value):
        if isinstance(value, Fixed60):
            self.value = getattr(value, "raw_value", 0)
        else:
            self.value = value
            
    @classmethod
    def from_int(cls, value):
        return cls(value * 216000)
        
    @classmethod
    def from_float(cls, value):
        return cls(int(round(value * 216000)))
        
    def _get_val(self, other):
        if hasattr(other, 'value'):
            return other.value
        elif isinstance(other, (int, float)):
            return int(round(other * 216000))
        raise TypeError(f"unsupported operand type(s) for Cortex: {type(other)}")

    def __add__(self, other):
        return Cortex(self.value + self._get_val(other))
        
    def __radd__(self, other):
        return Cortex(self._get_val(other) + self.value)
        
    def __sub__(self, other):
        return Cortex(self.value - self._get_val(other))
        
    def __rsub__(self, other):
        return Cortex(self._get_val(other) - self.value)
        
    def __mul__(self, other):
        return Cortex(int((self.value * self._get_val(other)) / 216000))
        
    def __rmul__(self, other):
        return Cortex(int((self._get_val(other) * self.value) / 216000))
        
    def mul(self, other):
        return self * other
        
    def __truediv__(self, other):
        return Cortex(int((self.value * 216000) / self._get_val(other)))
        
    def __rtruediv__(self, other):
        return Cortex(int((self._get_val(other) * 216000) / self.value))
        
    def __eq__(self, other):
        try:
            return self.value == self._get_val(other)
        except TypeError:
            return False
        
    def __lt__(self, other):
        return self.value < self._get_val(other)
        
    def __le__(self, other):
        return self.value <= self._get_val(other)
        
    def __gt__(self, other):
        return self.value > self._get_val(other)
        
    def __ge__(self, other):
        return self.value >= self._get_val(other)
        
    def __format__(self, format_spec):
        return format(float(self), format_spec)
        
    def __round__(self, ndigits=None):
        return round(float(self), ndigits)
        
    def __hash__(self):
        return hash(self.value)
        
    def __float__(self):
        return self.value / 216000.0
        
    def __int__(self):
        return int(self.value / 216000)
        
    def get_value(self):
        return self.value

    def to_float(self) -> float:
        return float(self)

def calculate_entropy_b60(data: bytes) -> Cortex:
    """Wrapper to return the Python-friendly Cortex object from Rust Fixed60."""
    return Cortex(_calc_entropy_rust(data))

Babylon60 = Cortex



