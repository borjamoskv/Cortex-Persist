# CORTEX Autodidact — Unified Dual Ledger (AX-041 → AX-046)
# Apache-2.0 · (c) 2026 CORTEX Swarm

"""Autodidact: Capital × Knowledge in a single hash-chain."""

from cortex.autodidact.dual_ledger import DualLedger, TxType
from cortex.autodidact.kv_cache import KVPrefixCache
from cortex.autodidact.pearl_staging import PeARLStagingValidator, StagingResult
from cortex.autodidact.ouroboros_bridge import OuroborosBridge
from cortex.autodidact.jit_synthesizer import JITSynthesizer

__all__ = [
    "DualLedger",
    "TxType",
    "KVPrefixCache",
    "PeARLStagingValidator",
    "StagingResult",
    "OuroborosBridge",
    "JITSynthesizer",
]
