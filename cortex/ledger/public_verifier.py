from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from cryptography.exceptions import InvalidSignature

from cortex.ledger.public_verifier_utils import (
    PublicVerifierError,
    _event_hash,
    _event_signature_scope,
    _has_error_prefix,
    _load_json_object,
    _loads_json_strict,
    _manifest_signature_scope,
    _merkle_root_v1,
    _parse_utc,
    _require_int,
    _require_str,
    _sha256_file,
    _string_list,
    _verify_ed25519,
)
from cortex.utils.canonical import canonical_json, compute_tx_hash

PUBLIC_V1_STRICT = "public-v1-strict"
LEGACY_V0 = "legacy-v0"
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
LEGACY_REQUIRED_FIELDS = frozenset(
    {"profile", "prev_hash", "project", "action", "detail", "timestamp", "expected_hash"}
)

ResultCode = Literal[
    "VALID_FULL_STRICT",
    "VALID_WITH_LIMITATIONS",
    "VALID_INTEGRITY_ONLY",
    "INVALID",
]


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


def verify_export(path: str | Path) -> dict[str, Any]:
    """Verify an exported public ledger package without SQLite, network, or runtime trust."""
    target = Path(path)
    if target.is_file():
        return _LegacyVectorVerifier([target]).verify()
    if _looks_like_legacy_vector_dir(target):
        return _LegacyVectorVerifier(sorted(target.glob("*.json"))).verify()
    return _PublicLedgerVerifier(VerificationInput.from_export_dir(target)).verify()


class _LegacyVectorVerifier:
    def __init__(self, vector_paths: Sequence[Path]) -> None:
        self.vector_paths = list(vector_paths)
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.hashes: list[str] = []
        self.artifacts: dict[str, str | None] = {}

    def verify(self) -> dict[str, Any]:
        if not self.vector_paths:
            self.errors.append("legacy_vector_missing")
        for path in self.vector_paths:
            self._verify_vector(path)
        guarantees = {name: False for name in REPORT_GUARANTEES}
        guarantees["integrity_verified"] = not self.errors and bool(self.hashes)
        guarantees["truth_verified"] = False
        guarantees["online_freshness_verified"] = False
        errors = sorted(set(self.errors))
        warnings = sorted(set(self.warnings))
        return {
            "profile": LEGACY_V0,
            "result": "INVALID" if errors else "VALID_INTEGRITY_ONLY",
            "guarantees": guarantees,
            "counts": {
                "vectors": len(self.hashes),
                "errors": len(errors),
                "warnings": len(warnings),
            },
            "artifacts": dict(sorted(self.artifacts.items())),
            "event_hashes": list(self.hashes),
            "errors": errors,
            "warnings": warnings,
        }

    def _verify_vector(self, path: Path) -> None:
        self.artifacts[path.name] = _sha256_file(path) if path.exists() else None
        value = _load_json_object(path, self.errors)
        if value is None:
            return
        missing = sorted(LEGACY_REQUIRED_FIELDS - value.keys())
        if missing:
            self.errors.append(
                f"legacy_vector_missing_required_fields:{path.name}:{','.join(missing)}"
            )
            return
        if value.get("profile") != LEGACY_V0:
            self.errors.append(
                f"legacy_vector_profile_unsupported:{path.name}:{value.get('profile')}"
            )
            return
        try:
            detail_json = canonical_json(value["detail"])
            actual_hash = compute_tx_hash(
                str(value["prev_hash"]),
                str(value["project"]),
                str(value["action"]),
                detail_json,
                str(value["timestamp"]),
            )
        except Exception as exc:
            self.errors.append(f"legacy_vector_hash_error:{path.name}:{exc.__class__.__name__}")
            return
        self.hashes.append(actual_hash)
        if actual_hash != value.get("expected_hash"):
            self.errors.append(f"legacy_vector_hash_mismatch:{path.name}")


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
            missing_error="public_keys_missing",
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
                value = _loads_json_strict(line)
            except json.JSONDecodeError as exc:
                self.errors.append(f"events_jsonl_invalid_json:{line_number}:{exc.msg}")
                continue
            except ValueError as exc:
                self.errors.append(f"events_jsonl_invalid_json:{line_number}:{exc}")
                continue
            if not isinstance(value, dict):
                self.errors.append(f"events_jsonl_non_object:{line_number}")
                continue
            events.append(value)

        if not events and not self.errors:
            self.errors.append("events_jsonl_empty")
        return events

    def _load_optional_object(
        self,
        path: Path,
        *,
        missing_warning: str | None = None,
        missing_error: str | None = None,
    ) -> dict[str, Any] | None:
        if not path.exists():
            if missing_error is not None:
                self.errors.append(missing_error)
            elif missing_warning is not None:
                self.warnings.append(missing_warning)
            return None
        return _load_json_object(path, self.errors)

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

            if previous_sequence is None and sequence != 1:
                self.errors.append(f"event_sequence_start_invalid:{index}:expected:1")
                replay_ok = False
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

            temporal_ok = temporal_ok and self._verify_event_time(event, index)
            key = self.key_index.get(str(event.get("actor_key_id")))
            if key is None:
                self.errors.append(f"event_actor_key_missing:{event_id}")
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
            self.errors,
            ("event_hash_", "event_chain_", "event_missing_", "event_unsupported_hash"),
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
        manifest = self.manifest
        if manifest is None:
            self.errors.append("manifest_missing")
            return False
        signature = manifest.get("signature")
        if not isinstance(signature, dict):
            self.errors.append("manifest_signature_missing")
            return False
        key_id = signature.get("key_id")
        value = signature.get("value")
        key = self.key_index.get(str(key_id))
        if key is None:
            self.errors.append(f"manifest_signature_key_missing:{key_id}")
            return False
        if "ledger.export" not in _string_list(key.get("permissions")):
            self.errors.append(f"manifest_signature_permission_denied:{key_id}")
            return False
        try:
            _verify_ed25519(
                _manifest_signature_scope(manifest),
                str(value),
                str(key["public_key"]),
            )
        except (InvalidSignature, PublicVerifierError, KeyError, TypeError, ValueError) as exc:
            self.errors.append(f"manifest_signature_invalid:{exc.__class__.__name__}")
            return False
        return True

    def _verify_manifest_file_hashes(self) -> bool:
        manifest = self.manifest
        if manifest is None:
            self.errors.append("manifest_missing")
            return False
        hashes = manifest.get("hashes")
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
            if _sha256_file(path) != expected_hash:
                self.errors.append(f"manifest_file_hash_mismatch:{field}")
                ok = False
        return ok

    def _verify_manifest_range(self) -> bool:
        manifest = self.manifest
        if manifest is None:
            self.errors.append("manifest_missing")
            return False
        if not self.events:
            self.errors.append("manifest_range_without_events")
            return False
        event_range = manifest.get("range")
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
        manifest = self.manifest
        if manifest is None:
            self.errors.append("manifest_missing")
            return False
        hashes = manifest.get("hashes")
        if not isinstance(hashes, dict):
            return False
        expected_root = hashes.get("merkle_root")
        if not isinstance(expected_root, str):
            self.errors.append("manifest_merkle_root_missing")
            return False
        if _merkle_root_v1(self.event_hashes) != expected_root:
            self.errors.append("manifest_merkle_root_mismatch")
            return False
        return True

    def _verify_manifest_counts(self) -> bool:
        manifest = self.manifest
        if manifest is None:
            self.errors.append("manifest_missing")
            return False
        counts = manifest.get("counts")
        if not isinstance(counts, dict):
            self.errors.append("manifest_counts_missing")
            return False
        if counts.get("event_count") != len(self.events):
            self.errors.append("manifest_event_count_mismatch")
            return False
        return True

    def _verify_manifest_scope(self) -> bool:
        manifest = self.manifest
        if manifest is None:
            self.errors.append("manifest_missing")
            return False
        stream_id = manifest.get("stream_id")
        tenant_id = manifest.get("tenant_id")
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
        manifest = self.manifest
        if manifest is None:
            return False
        signature = manifest.get("signature")
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


def _looks_like_legacy_vector_dir(path: Path) -> bool:
    if not path.is_dir() or (path / "events.jsonl").exists():
        return False
    return any(child.name.startswith("legacy_v0_vector_") for child in path.glob("*.json"))
