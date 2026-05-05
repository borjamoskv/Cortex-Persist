from __future__ import annotations

import base64
import binascii
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

PUBLIC_V1_STRICT = "public-v1-strict"
REPORT_GUARANTEES = (
    "integrity_verified",
    "origin_authenticity_verified",
    "authority_verified",
    "replay_consistency_verified",
    "temporal_consistency_verified",
    "online_freshness_verified",
    "completeness_verified",
    "truth_verified",
)
STRICT_REQUIRED_EVENT_FIELDS = frozenset(
    {
        "schema_version",
        "stream_id",
        "tenant_id",
        "sequence",
        "event_id",
        "nonce",
        "issued_at",
        "recorded_at",
        "actor_id",
        "actor_key_id",
        "action",
        "project",
        "target",
        "detail",
        "prev_hash",
        "hash_alg",
        "hash",
        "signature_alg",
        "origin_signature",
    }
)

ResultCode = Literal["VALID_FULL_STRICT", "VALID_WITH_LIMITATIONS", "INVALID"]


class PublicVerifierError(ValueError):
    """Input cannot be parsed as a public ledger export."""


@dataclass(frozen=True)
class VerificationInput:
    export_dir: Path
    events_path: Path
    manifest_path: Path
    public_keys_path: Path
    key_events_path: Path
    schema_path: Path
    verification_profile_path: Path

    @staticmethod
    def from_export_dir(export_dir: str | Path) -> VerificationInput:
        root = Path(export_dir)
        return VerificationInput(
            export_dir=root,
            events_path=root / "events.jsonl",
            manifest_path=root / "manifest.json",
            public_keys_path=root / "public-keys.json",
            key_events_path=root / "key-events.jsonl",
            schema_path=root / "schema.json",
            verification_profile_path=root / "verification-profile.json",
        )


def verify_export(export_dir: str | Path) -> dict[str, Any]:
    """Verify an exported public ledger package without SQLite, network, or runtime trust."""
    verifier = _PublicLedgerVerifier(VerificationInput.from_export_dir(export_dir))
    return verifier.verify()


class _PublicLedgerVerifier:
    def __init__(self, paths: VerificationInput) -> None:
        self.paths = paths
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.events: list[dict[str, Any]] = []
        self.key_registry: dict[str, Any] | None = None
        self.key_index: dict[str, dict[str, Any]] = {}
        self.manifest: dict[str, Any] | None = None
        self.event_hashes: list[str] = []
        self.guarantees: dict[str, bool] = {name: False for name in REPORT_GUARANTEES}

    def verify(self) -> dict[str, Any]:
        self.events = self._load_events()
        self.key_registry = self._load_optional_object(
            self.paths.public_keys_path,
            missing_warning="public_keys_missing",
        )
        if self.key_registry is not None:
            self.key_index = self._build_key_index(self.key_registry)
        self.manifest = self._load_optional_object(
            self.paths.manifest_path,
            missing_warning="manifest_missing",
        )

        self._verify_events()
        self._verify_manifest()
        self._finalize_guarantees()
        return self._report()

    def _load_events(self) -> list[dict[str, Any]]:
        if not self.paths.events_path.exists():
            self.errors.append("events_jsonl_missing")
            return []

        events: list[dict[str, Any]] = []
        try:
            lines = self.paths.events_path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            self.errors.append(f"events_jsonl_unreadable:{exc.__class__.__name__}")
            return []

        for line_number, line in enumerate(lines, start=1):
            if not line:
                self.errors.append(f"events_jsonl_blank_line:{line_number}")
                continue
            try:
                value = json.loads(line, object_pairs_hook=_reject_duplicate_keys)
            except json.JSONDecodeError as exc:
                self.errors.append(f"events_jsonl_invalid_json:{line_number}:{exc.msg}")
                continue
            except ValueError as exc:
                self.errors.append(f"events_jsonl_invalid_json:{line_number}:{exc}")
                continue
            if not isinstance(value, dict):
                self.errors.append(f"events_jsonl_non_object:{line_number}")
                continue
            if _contains_float(value):
                self.errors.append(f"events_jsonl_float_not_allowed:{line_number}")
                continue
            events.append(value)

        if not events and not self.errors:
            self.errors.append("events_jsonl_empty")
        return events

    def _load_optional_object(self, path: Path, *, missing_warning: str) -> dict[str, Any] | None:
        if not path.exists():
            self.warnings.append(missing_warning)
            return None
        try:
            value = json.loads(
                path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
            )
        except json.JSONDecodeError as exc:
            self.errors.append(f"{path.name}_invalid_json:{exc.msg}")
            return None
        except (OSError, ValueError) as exc:
            self.errors.append(f"{path.name}_unreadable:{exc.__class__.__name__}:{exc}")
            return None
        if not isinstance(value, dict):
            self.errors.append(f"{path.name}_non_object")
            return None
        if _contains_float(value):
            self.errors.append(f"{path.name}_float_not_allowed")
            return None
        return value

    def _build_key_index(self, registry: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        keys = registry.get("keys")
        if not isinstance(keys, list):
            self.errors.append("public_keys_missing_keys_array")
            return {}

        index: dict[str, dict[str, Any]] = {}
        for key in keys:
            if not isinstance(key, dict):
                self.errors.append("public_keys_non_object_key")
                continue
            key_id = key.get("key_id")
            if not isinstance(key_id, str) or not key_id:
                self.errors.append("public_keys_missing_key_id")
                continue
            if key_id in index:
                self.errors.append(f"public_keys_duplicate_key_id:{key_id}")
                continue
            index[key_id] = key
        return index

    def _verify_events(self) -> None:
        seen_event_ids: set[str] = set()
        seen_nonces: set[str] = set()
        previous_hash = "GENESIS"
        previous_sequence: int | None = None
        integrity_ok = bool(self.events)
        origin_ok = bool(self.events) and bool(self.key_index)
        authority_ok = bool(self.events) and bool(self.key_index)
        replay_ok = bool(self.events)
        temporal_ok = bool(self.events)

        for index, event in enumerate(self.events, start=1):
            missing = sorted(STRICT_REQUIRED_EVENT_FIELDS - event.keys())
            if missing:
                self.errors.append(f"event_missing_required_fields:{index}:{','.join(missing)}")
                integrity_ok = False
                origin_ok = False
                authority_ok = False
                replay_ok = False
                temporal_ok = False
                continue

            if event.get("hash_alg") != "sha256":
                self.errors.append(f"event_unsupported_hash_alg:{index}:{event.get('hash_alg')}")
                integrity_ok = False
            if event.get("signature_alg") != "ed25519":
                self.errors.append(
                    f"event_unsupported_signature_alg:{index}:{event.get('signature_alg')}"
                )
                origin_ok = False

            event_id = _require_str(event, "event_id", index, self.errors)
            nonce = _require_str(event, "nonce", index, self.errors)
            sequence = _require_int(event, "sequence", index, self.errors)
            if event_id in seen_event_ids:
                self.errors.append(f"event_replay_duplicate_event_id:{event_id}")
                replay_ok = False
            seen_event_ids.add(event_id)
            if nonce in seen_nonces:
                self.errors.append(f"event_replay_duplicate_nonce:{nonce}")
                replay_ok = False
            seen_nonces.add(nonce)

            if previous_sequence is not None and sequence != previous_sequence + 1:
                self.errors.append(f"event_sequence_gap:{index}:expected:{previous_sequence + 1}")
                replay_ok = False
            previous_sequence = sequence

            prev_hash = _require_str(event, "prev_hash", index, self.errors)
            if prev_hash != previous_hash:
                self.errors.append(f"event_chain_break:{index}:expected:{previous_hash}")
                integrity_ok = False

            computed_hash = _event_hash(event)
            expected_hash = _require_str(event, "hash", index, self.errors)
            self.event_hashes.append(expected_hash)
            if computed_hash != expected_hash:
                self.errors.append(f"event_hash_mismatch:{event_id}")
                integrity_ok = False
            previous_hash = expected_hash

            event_temporal_ok = self._verify_event_time(event, index)
            temporal_ok = temporal_ok and event_temporal_ok

            key = self.key_index.get(str(event.get("actor_key_id")))
            if key is None:
                self.warnings.append(f"event_actor_key_missing:{event_id}")
                origin_ok = False
                authority_ok = False
                temporal_ok = False
                continue

            if key.get("actor_id") != event.get("actor_id"):
                self.errors.append(f"event_actor_key_actor_mismatch:{event_id}")
                authority_ok = False
            if key.get("algorithm") != "ed25519":
                self.errors.append(f"event_actor_key_unsupported_algorithm:{event_id}")
                origin_ok = False
            if event.get("action") not in _string_list(key.get("permissions")):
                self.errors.append(f"event_actor_key_permission_denied:{event_id}")
                authority_ok = False
            if not self._key_valid_for_event(key, event, index):
                temporal_ok = False
                authority_ok = False

            try:
                _verify_ed25519(
                    _event_signature_scope(event),
                    str(event["origin_signature"]),
                    str(key["public_key"]),
                )
            except (InvalidSignature, PublicVerifierError, KeyError, TypeError, ValueError) as exc:
                self.errors.append(
                    f"event_origin_signature_invalid:{event_id}:{exc.__class__.__name__}"
                )
                origin_ok = False

        self.guarantees["integrity_verified"] = integrity_ok and not _has_error_prefix(
            self.errors, ("event_hash_", "event_chain_", "event_missing_", "event_unsupported_hash")
        )
        self.guarantees["origin_authenticity_verified"] = origin_ok
        self.guarantees["authority_verified"] = authority_ok
        self.guarantees["replay_consistency_verified"] = replay_ok
        self.guarantees["temporal_consistency_verified"] = temporal_ok

    def _verify_event_time(self, event: Mapping[str, Any], index: int) -> bool:
        try:
            issued_at = _parse_utc(str(event["issued_at"]))
            recorded_at = _parse_utc(str(event["recorded_at"]))
        except (KeyError, PublicVerifierError) as exc:
            self.errors.append(f"event_timestamp_invalid:{index}:{exc.__class__.__name__}")
            return False
        if recorded_at < issued_at:
            self.errors.append(f"event_recorded_before_issued:{index}")
            return False
        return True

    def _key_valid_for_event(
        self,
        key: Mapping[str, Any],
        event: Mapping[str, Any],
        index: int,
    ) -> bool:
        try:
            issued_at = _parse_utc(str(event["issued_at"]))
            valid_from = _parse_utc(str(key["valid_from"]))
            valid_until = _parse_utc(str(key["valid_until"]))
        except (KeyError, PublicVerifierError) as exc:
            self.errors.append(f"event_key_validity_invalid:{index}:{exc.__class__.__name__}")
            return False
        if key.get("status") != "active":
            self.errors.append(f"event_key_not_active:{index}")
            return False
        if not valid_from <= issued_at <= valid_until:
            self.errors.append(f"event_key_outside_validity:{index}")
            return False
        return True

    def _verify_manifest(self) -> None:
        if self.manifest is None:
            return

        manifest_signature_ok = self._verify_manifest_signature()
        file_hashes_ok = self._verify_manifest_file_hashes()
        range_ok = self._verify_manifest_range()
        merkle_ok = self._verify_manifest_merkle()
        counts_ok = self._verify_manifest_counts()
        manifest_scope_ok = self._verify_manifest_scope()

        self.guarantees["completeness_verified"] = (
            manifest_signature_ok
            and file_hashes_ok
            and range_ok
            and merkle_ok
            and counts_ok
            and manifest_scope_ok
            and self.guarantees["integrity_verified"]
        )

    def _verify_manifest_signature(self) -> bool:
        assert self.manifest is not None
        signature = self.manifest.get("signature")
        if not isinstance(signature, dict):
            self.errors.append("manifest_signature_missing")
            return False
        key_id = signature.get("key_id")
        value = signature.get("value")
        key = self.key_index.get(str(key_id))
        if key is None:
            self.warnings.append(f"manifest_signature_key_missing:{key_id}")
            return False
        if "ledger.export" not in _string_list(key.get("permissions")):
            self.errors.append(f"manifest_signature_permission_denied:{key_id}")
            return False
        try:
            _verify_ed25519(
                _manifest_signature_scope(self.manifest), str(value), str(key["public_key"])
            )
        except (InvalidSignature, PublicVerifierError, KeyError, TypeError, ValueError) as exc:
            self.errors.append(f"manifest_signature_invalid:{exc.__class__.__name__}")
            return False
        return True

    def _verify_manifest_file_hashes(self) -> bool:
        assert self.manifest is not None
        hashes = self.manifest.get("hashes")
        if not isinstance(hashes, dict):
            self.errors.append("manifest_hashes_missing")
            return False
        expected = {
            "events_file_sha256": self.paths.events_path,
            "schema_file_sha256": self.paths.schema_path,
            "public_keys_file_sha256": self.paths.public_keys_path,
            "key_events_file_sha256": self.paths.key_events_path,
            "verification_profile_sha256": self.paths.verification_profile_path,
        }
        ok = True
        for field, path in expected.items():
            expected_hash = hashes.get(field)
            if not isinstance(expected_hash, str):
                self.errors.append(f"manifest_hash_missing:{field}")
                ok = False
                continue
            if not path.exists():
                self.errors.append(f"manifest_file_missing:{path.name}")
                ok = False
                continue
            actual_hash = _sha256_file(path)
            if actual_hash != expected_hash:
                self.errors.append(f"manifest_file_hash_mismatch:{field}")
                ok = False
        return ok

    def _verify_manifest_range(self) -> bool:
        assert self.manifest is not None
        if not self.events:
            self.errors.append("manifest_range_without_events")
            return False
        event_range = self.manifest.get("range")
        if not isinstance(event_range, dict):
            self.errors.append("manifest_range_missing")
            return False
        first = self.events[0]
        last = self.events[-1]
        expected = {
            "first_sequence": first.get("sequence"),
            "last_sequence": last.get("sequence"),
            "first_recorded_at": first.get("recorded_at"),
            "last_recorded_at": last.get("recorded_at"),
        }
        ok = True
        for field, expected_value in expected.items():
            if event_range.get(field) != expected_value:
                self.errors.append(f"manifest_range_mismatch:{field}")
                ok = False
        return ok

    def _verify_manifest_merkle(self) -> bool:
        assert self.manifest is not None
        hashes = self.manifest.get("hashes")
        if not isinstance(hashes, dict):
            return False
        expected_root = hashes.get("merkle_root")
        if not isinstance(expected_root, str):
            self.errors.append("manifest_merkle_root_missing")
            return False
        actual_root = _merkle_root_v1(self.event_hashes)
        if actual_root != expected_root:
            self.errors.append("manifest_merkle_root_mismatch")
            return False
        return True

    def _verify_manifest_counts(self) -> bool:
        assert self.manifest is not None
        counts = self.manifest.get("counts")
        if not isinstance(counts, dict):
            self.errors.append("manifest_counts_missing")
            return False
        if counts.get("event_count") != len(self.events):
            self.errors.append("manifest_event_count_mismatch")
            return False
        return True

    def _verify_manifest_scope(self) -> bool:
        assert self.manifest is not None
        stream_id = self.manifest.get("stream_id")
        tenant_id = self.manifest.get("tenant_id")
        ok = True
        for event in self.events:
            if event.get("stream_id") != stream_id:
                self.errors.append(f"manifest_stream_mismatch:{event.get('event_id')}")
                ok = False
            if event.get("tenant_id") != tenant_id:
                self.errors.append(f"manifest_tenant_mismatch:{event.get('event_id')}")
                ok = False
        return ok

    def _finalize_guarantees(self) -> None:
        self.guarantees["online_freshness_verified"] = False
        self.guarantees["truth_verified"] = False

        if self.manifest is not None and self.guarantees["completeness_verified"]:
            self.guarantees["authority_verified"] = (
                self.guarantees["authority_verified"] and self._manifest_export_authority_ok()
            )

    def _manifest_export_authority_ok(self) -> bool:
        assert self.manifest is not None
        signature = self.manifest.get("signature")
        if not isinstance(signature, dict):
            return False
        key = self.key_index.get(str(signature.get("key_id")))
        return key is not None and "ledger.export" in _string_list(key.get("permissions"))

    def _report(self) -> dict[str, Any]:
        errors = sorted(set(self.errors))
        warnings = sorted(set(self.warnings))
        result = _result_code(self.guarantees, errors)
        return {
            "profile": PUBLIC_V1_STRICT,
            "result": result,
            "guarantees": {name: bool(self.guarantees[name]) for name in REPORT_GUARANTEES},
            "counts": {
                "events": len(self.events),
                "errors": len(errors),
                "warnings": len(warnings),
            },
            "artifacts": self._artifact_hashes(),
            "event_hashes": list(self.event_hashes),
            "errors": errors,
            "warnings": warnings,
        }

    def _artifact_hashes(self) -> dict[str, str | None]:
        artifacts = {
            "events.jsonl": self.paths.events_path,
            "manifest.json": self.paths.manifest_path,
            "public-keys.json": self.paths.public_keys_path,
            "key-events.jsonl": self.paths.key_events_path,
            "schema.json": self.paths.schema_path,
            "verification-profile.json": self.paths.verification_profile_path,
        }
        return {
            artifact_name: _sha256_file(path) if path.exists() else None
            for artifact_name, path in artifacts.items()
        }


def _result_code(guarantees: Mapping[str, bool], errors: Sequence[str]) -> ResultCode:
    if errors:
        return "INVALID"
    required_offline_guarantees = (
        "integrity_verified",
        "origin_authenticity_verified",
        "authority_verified",
        "replay_consistency_verified",
        "temporal_consistency_verified",
        "completeness_verified",
    )
    if all(guarantees[name] for name in required_offline_guarantees):
        return "VALID_FULL_STRICT"
    return "VALID_WITH_LIMITATIONS"


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"duplicate JSON key: {key}")
        seen.add(key)
        out[key] = value
    return out


def _contains_float(value: Any) -> bool:
    if isinstance(value, float):
        return True
    if isinstance(value, Mapping):
        return any(_contains_float(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_float(child) for child in value)
    return False


def _canonical_json(value: Any) -> str:
    if _contains_float(value):
        raise PublicVerifierError("float_not_allowed")
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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
    return _sha256_bytes(_canonical_json(scope).encode("utf-8"))


def _event_signature_scope(event: Mapping[str, Any]) -> bytes:
    scope = dict(event)
    scope.pop("origin_signature", None)
    return _canonical_json(scope).encode("utf-8")


def _manifest_signature_scope(manifest: Mapping[str, Any]) -> bytes:
    scope = dict(manifest)
    scope.pop("signature", None)
    return _canonical_json(scope).encode("utf-8")


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
                next_nodes.append(
                    _sha256_bytes(("CORTEX-MERKLE-NODE-v1:" + left + right).encode("utf-8"))
                )
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
