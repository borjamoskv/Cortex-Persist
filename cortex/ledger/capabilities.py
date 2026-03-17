from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeCapabilities:
    ledger_write: bool = True
    embeddings: bool = False
    vector_index: bool = False
    causal_tracing: bool = False
    oracle_verify: bool = False
    degraded_mode: bool = True
    provider_name: str = "null"
