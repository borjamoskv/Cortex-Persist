"""
[C5-REAL] MOSKV-1 Asymmetric ZK Compiler Types
"""

from typing import Optional

from typing_extensions import TypedDict


class CompilerResult(TypedDict):
    circuit_name: str
    ast_hash: str
    applied_invariants: list[str]
    prover_time_reduction_expected: str
    compilation_time_ms: float
    status: str
    optimized_source: str
    cortex_taint: str
    ledger_hash: Optional[str]
    cortex_taint_error: Optional[str]
