# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from babylon60.ledger.ledger_core import SovereignLedger
    from babylon60.ledger.models import LedgerEvent, LedgerOriginSignature, SemanticStatus
    from babylon60.ledger.origin import (
        OriginKeyRecord,
        OriginKeyRegistry,
        OriginSignatureError,
        OriginSignaturePolicy,
        origin_payload_hash,
        sign_event_origin,
        verify_event_origin,
    )
    from babylon60.ledger.queue import EnrichmentQueue
    from babylon60.ledger.replay import (
        ReplayAdmissionError,
        ReplayAdmissionPolicy,
        ReplayAdmissionResult,
        replay_request_hash,
        validate_batch_import_manifest,
    )
    from babylon60.ledger.store import LedgerStore
    from babylon60.ledger.verifier import LedgerVerifier
    from babylon60.ledger.writer import LedgerWriter

__all__ = [
    "EnrichmentQueue",
    "ImmutableLedger",  # pyright: ignore[reportUnsupportedDunderAll]
    "LedgerEvent",
    "LedgerOriginSignature",
    "LedgerStore",
    "LedgerVerifier",
    "LedgerWriter",
    "OriginKeyRecord",
    "OriginKeyRegistry",
    "OriginSignatureError",
    "OriginSignaturePolicy",
    "ReplayAdmissionError",
    "ReplayAdmissionPolicy",
    "ReplayAdmissionResult",
    "SemanticStatus",
    "SovereignLedger",
    "origin_payload_hash",
    "replay_request_hash",
    "sign_event_origin",
    "validate_batch_import_manifest",
    "verify_event_origin",
]

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "LedgerEvent": ("cortex.ledger.models", "LedgerEvent"),
    "LedgerOriginSignature": ("cortex.ledger.models", "LedgerOriginSignature"),
    "SemanticStatus": ("cortex.ledger.models", "SemanticStatus"),
    "LedgerStore": ("cortex.ledger.store", "LedgerStore"),
    "LedgerWriter": ("cortex.ledger.writer", "LedgerWriter"),
    "LedgerVerifier": ("cortex.ledger.verifier", "LedgerVerifier"),
    "EnrichmentQueue": ("cortex.ledger.queue", "EnrichmentQueue"),
    "OriginKeyRecord": ("cortex.ledger.origin", "OriginKeyRecord"),
    "OriginKeyRegistry": ("cortex.ledger.origin", "OriginKeyRegistry"),
    "OriginSignatureError": ("cortex.ledger.origin", "OriginSignatureError"),
    "OriginSignaturePolicy": ("cortex.ledger.origin", "OriginSignaturePolicy"),
    "origin_payload_hash": ("cortex.ledger.origin", "origin_payload_hash"),
    "sign_event_origin": ("cortex.ledger.origin", "sign_event_origin"),
    "verify_event_origin": ("cortex.ledger.origin", "verify_event_origin"),
    "ReplayAdmissionError": ("cortex.ledger.replay", "ReplayAdmissionError"),
    "ReplayAdmissionPolicy": ("cortex.ledger.replay", "ReplayAdmissionPolicy"),
    "ReplayAdmissionResult": ("cortex.ledger.replay", "ReplayAdmissionResult"),
    "replay_request_hash": ("cortex.ledger.replay", "replay_request_hash"),
    "validate_batch_import_manifest": (
        "cortex.ledger.replay",
        "validate_batch_import_manifest",
    ),
}


def __getattr__(name: str):
    if name in {"SovereignLedger", "ImmutableLedger"}:
        module = importlib.import_module("cortex.ledger.ledger_core")
        ledger_cls = module.SovereignLedger
        globals()["SovereignLedger"] = ledger_cls
        globals()["ImmutableLedger"] = ledger_cls
        return ledger_cls
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'cortex.ledger' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
