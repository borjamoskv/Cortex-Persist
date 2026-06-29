# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import base64
import binascii
import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from babylon60.crypto.hash_registry import cortex_hash


class PublicVerifierError(ValueError):
    """Input cannot be parsed as a public ledger export."""


def _load_json_object(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        value = _loads_json_strict(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{path.name}_invalid_json:{exc.msg}")
        return None
    except OSError as exc:
        errors.append(f"{path.name}_unreadable:{exc.__class__.__name__}")
        return None
    except ValueError as exc:
        errors.append(f"{path.name}_invalid_json:{exc}")
        return None
    if not isinstance(value, dict):
        errors.append(f"{path.name}_non_object")
        return None
    return value


def _loads_json_strict(text: str) -> Any:
    return json.loads(
        text,
        object_pairs_hook=_reject_duplicate_keys,
        parse_float=_reject_float,
        parse_constant=_reject_constant,
    )


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"duplicate JSON key: {key}")
        seen.add(key)
        out[key] = value
    return out


def _reject_float(value: str) -> None:
    raise ValueError(f"float_not_allowed:{value}")


def _reject_constant(value: str) -> None:
    raise ValueError(f"constant_not_allowed:{value}")


def _canonical_public_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256_bytes(value: bytes) -> str:
    return cortex_hash(value)


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _b64url_decode(value: str) -> bytes:
    if not value:
        raise PublicVerifierError("empty_base64url")
    padding = "=" * (-len(value) % 4)
    try:
        return base64.b64decode((value + padding).encode("ascii"), altchars=b"-_", validate=True)
    except (binascii.Error, UnicodeEncodeError) as exc:
        raise PublicVerifierError("invalid_base64url") from exc


def _verify_ed25519(payload: bytes, signature_b64url: str, public_key_b64url: str) -> None:
    public_key = Ed25519PublicKey.from_public_bytes(_b64url_decode(public_key_b64url))
    public_key.verify(_b64url_decode(signature_b64url), payload)


def _event_hash(event: Mapping[str, Any]) -> str:
    scope = dict(event)
    scope.pop("hash", None)
    scope.pop("origin_signature", None)
    return _sha256_bytes(_canonical_public_json(scope).encode("utf-8"))


def _event_signature_scope(event: Mapping[str, Any]) -> bytes:
    scope = dict(event)
    scope.pop("origin_signature", None)
    return _canonical_public_json(scope).encode("utf-8")


def _manifest_signature_scope(manifest: Mapping[str, Any]) -> bytes:
    scope = dict(manifest)
    scope.pop("signature", None)
    return _canonical_public_json(scope).encode("utf-8")


def _merkle_root_v1(event_hashes: Sequence[str]) -> str:
    nodes = [
        _sha256_bytes(("CORTEX-MERKLE-LEAF-v1:" + event_hash).encode("utf-8"))
        for event_hash in event_hashes
    ]
    if not nodes:
        return _sha256_bytes(b"CORTEX-MERKLE-EMPTY-v1")

    while len(nodes) > 1:
        next_nodes: list[str] = []
        for index in range(0, len(nodes), 2):
            left = nodes[index]
            right = nodes[index + 1] if index + 1 < len(nodes) else None
            if right is None:
                next_nodes.append(left)
            else:
                payload = "CORTEX-MERKLE-NODE-v1:" + left + right
                next_nodes.append(_sha256_bytes(payload.encode("utf-8")))
        nodes = next_nodes
    return nodes[0]


def _parse_utc(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise PublicVerifierError("invalid_timestamp") from exc
    if parsed.tzinfo is None:
        raise PublicVerifierError("timestamp_missing_timezone")
    return parsed


def _require_str(
    event: Mapping[str, Any],
    field: str,
    index: int,
    errors: list[str],
) -> str:
    value = event.get(field)
    if not isinstance(value, str) or not value:
        errors.append(f"event_field_invalid:{index}:{field}")
        return ""
    return value


def _require_int(
    event: Mapping[str, Any],
    field: str,
    index: int,
    errors: list[str],
) -> int:
    value = event.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"event_field_invalid:{index}:{field}")
        return 0
    return value


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _has_error_prefix(errors: Sequence[str], prefixes: Sequence[str]) -> bool:
    return any(error.startswith(tuple(prefixes)) for error in errors)
