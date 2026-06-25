# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from legacy_research.ledger.public_verifier_utils import (
    _load_json_object,
    _loads_json_strict,
)

if TYPE_CHECKING:
    from legacy_research.ledger._types import PublicVerifierProtocol as _PublicLedgerVerifier


def load_events(verifier: _PublicLedgerVerifier) -> list[dict[str, Any]]:
    if not verifier.paths.events_path.exists():
        verifier.errors.append("events_jsonl_missing")
        return []

    events: list[dict[str, Any]] = []
    try:
        lines = verifier.paths.events_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        verifier.errors.append(f"events_jsonl_unreadable:{exc.__class__.__name__}")
        return []

    for line_number, line in enumerate(lines, start=1):
        if not line:
            verifier.errors.append(f"events_jsonl_blank_line:{line_number}")
            continue
        try:
            value = _loads_json_strict(line)
        except json.JSONDecodeError as exc:
            verifier.errors.append(f"events_jsonl_invalid_json:{line_number}:{exc.msg}")
            continue
        except ValueError as exc:
            verifier.errors.append(f"events_jsonl_invalid_json:{line_number}:{exc}")
            continue
        if not isinstance(value, dict):
            verifier.errors.append(f"events_jsonl_non_object:{line_number}")
            continue
        events.append(value)

    if not events and not verifier.errors:
        verifier.errors.append("events_jsonl_empty")
    return events


def load_checkpoints(verifier: _PublicLedgerVerifier) -> list[dict[str, Any]]:
    if not verifier.paths.checkpoints_path or not verifier.paths.checkpoints_path.exists():
        return []

    checkpoints: list[dict[str, Any]] = []
    try:
        lines = verifier.paths.checkpoints_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        verifier.errors.append(f"checkpoints_jsonl_unreadable:{exc.__class__.__name__}")
        return []

    for line_number, line in enumerate(lines, start=1):
        if not line:
            continue
        try:
            value = _loads_json_strict(line)
        except json.JSONDecodeError as exc:
            verifier.errors.append(f"checkpoints_jsonl_invalid_json:{line_number}:{exc.msg}")
            continue
        except ValueError as exc:
            verifier.errors.append(f"checkpoints_jsonl_invalid_json:{line_number}:{exc}")
            continue
        if not isinstance(value, dict):
            verifier.errors.append(f"checkpoints_jsonl_non_object:{line_number}")
            continue
        checkpoints.append(value)

    return checkpoints


def load_optional_object(
    verifier: _PublicLedgerVerifier,
    path: Path,
    *,
    missing_warning: str | None = None,
    missing_error: str | None = None,
) -> dict[str, Any] | None:
    if not path.exists():
        if missing_error is not None:
            verifier.errors.append(missing_error)
        elif missing_warning is not None:
            verifier.warnings.append(missing_warning)
        return None
    return _load_json_object(path, verifier.errors)


def build_key_index(
    verifier: _PublicLedgerVerifier, registry: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    keys = registry.get("keys")
    if not isinstance(keys, list):
        verifier.errors.append("public_keys_missing_keys_array")
        return {}

    index: dict[str, dict[str, Any]] = {}
    for key in keys:
        if not isinstance(key, dict):
            verifier.errors.append("public_keys_non_object_key")
            continue
        key_id = key.get("key_id")
        if not isinstance(key_id, str) or not key_id:
            verifier.errors.append("public_keys_missing_key_id")
            continue
        if key_id in index:
            verifier.errors.append(f"public_keys_duplicate_key_id:{key_id}")
            continue
        index[key_id] = key
    return index
