from __future__ import annotations

import base64
import json
import os
import stat
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from cortex.ledger.public_verifier import STRICT_REQUIRED_EVENT_FIELDS, verify_export
from cortex.ledger.public_verifier_utils import (
    _canonical_public_json,
    _event_hash,
    _merkle_root_v1,
    _sha256_file,
)

PUBLIC_EXPORT_MANIFEST_VERSION = "cortex-forensic-export-manifest-v1"
KEY_REGISTRY_VERSION = "cortex-key-registry-v1"
EVENT_SCHEMA_VERSION = "cortex-ledger-event-schema-v1"
VERIFICATION_PROFILE_VERSION = "cortex-verification-profile-v1"
LEGACY_LIMITATIONS = (
    "legacy_v0_integrity_only",
    "origin_authenticity_not_verified",
    "manifest_completeness_not_available",
)
PUBLIC_EXPORT_FILES = frozenset(
    {
        "events.jsonl",
        "key-events.jsonl",
        "manifest.json",
        "public-keys.json",
        "schema.json",
        "verification-profile.json",
        "verification-report.json",
    }
)
FORBIDDEN_EXPORT_TOKENS = (
    "private_key",
    "seed_hex",
    "begin private key",
    "api_key",
    "secret_key",
    "password",
)
EXECUTABLE_SUFFIXES = (".bat", ".cmd", ".exe", ".js", ".mjs", ".py", ".sh")


@dataclass(frozen=True)
class ExportAuthority:
    key_id: str
    actor_id: str
    private_key: Ed25519PrivateKey
    environment: str = "test"


@dataclass(frozen=True)
class LedgerExportResult:
    export_dir: Path
    manifest_path: Path
    events_path: Path
    public_keys_path: Path
    verification_report_path: Path | None
    manifest_hash: str
    verification_result: str | None


@dataclass(frozen=True)
class LegacyLedgerExportResult:
    export_dir: Path
    vector_paths: tuple[Path, ...]
    limitations_path: Path
    verification_result: str
    limitations: tuple[str, ...]


def write_public_ledger_export(
    *,
    events: Sequence[Mapping[str, Any]],
    export_dir: str | Path,
    public_keys: Sequence[Mapping[str, Any]],
    export_authority: ExportAuthority,
    export_id: str,
    tenant_id: str,
    stream_id: str,
    purpose: str = "forensic_ledger_export",
    environment: str = "test",
    created_at: str | None = None,
    key_events: Sequence[Mapping[str, Any]] = (),
    include_verification_report: bool = False,
    allow_overwrite: bool = False,
) -> LedgerExportResult:
    """Write a signed public ledger export package without exporting fact payloads."""
    if not events:
        raise ValueError("at least one ledger event is required")

    root = Path(export_dir)
    _prepare_export_dir(root, allow_overwrite=allow_overwrite)

    event_objects = [dict(event) for event in events]
    key_objects = [dict(key) for key in public_keys]
    event_hashes = _validate_public_events(
        event_objects,
        tenant_id=tenant_id,
        stream_id=stream_id,
    )
    _validate_public_key_records(key_objects)
    key_event_objects = [dict(event) for event in key_events]
    _assert_no_private_material(
        {
            "events": event_objects,
            "key_events": key_event_objects,
            "public_keys": key_objects,
        }
    )

    generated_at = created_at or _utc_now()
    events_path = root / "events.jsonl"
    public_keys_path = root / "public-keys.json"
    key_events_path = root / "key-events.jsonl"
    schema_path = root / "schema.json"
    verification_profile_path = root / "verification-profile.json"
    manifest_path = root / "manifest.json"
    verification_report_path = root / "verification-report.json"

    _write_text_atomic(
        events_path,
        "".join(_canonical_public_json(event) + "\n" for event in event_objects),
    )
    _write_text_atomic(
        key_events_path,
        "".join(_canonical_public_json(event) + "\n" for event in key_event_objects),
    )
    _write_json_atomic(schema_path, _schema_document())
    _write_json_atomic(verification_profile_path, _verification_profile_document())
    _write_json_atomic(
        public_keys_path,
        _key_registry_document(
            tenant_id=tenant_id,
            public_keys=key_objects,
            export_authority=export_authority,
            generated_at=generated_at,
        ),
    )

    manifest_without_signature = _manifest_document(
        events=event_objects,
        event_hashes=event_hashes,
        export_id=export_id,
        tenant_id=tenant_id,
        stream_id=stream_id,
        created_by=export_authority.actor_id,
        created_at=generated_at,
        purpose=purpose,
        environment=environment,
        root=root,
    )
    manifest = dict(manifest_without_signature)
    manifest["signature"] = {
        "key_id": export_authority.key_id,
        "signature_scope": "canonical_manifest_without_signature",
        "value": _b64url_encode(
            export_authority.private_key.sign(
                _canonical_public_json(manifest_without_signature).encode("utf-8")
            )
        ),
    }
    _write_json_atomic(manifest_path, manifest)

    verification_result: str | None = None
    if include_verification_report:
        report = verify_export(root)
        verification_result = str(report["result"])
        _write_json_atomic(verification_report_path, report)
    else:
        verification_report_path = None

    _scan_export_safety(root)

    return LedgerExportResult(
        export_dir=root,
        manifest_path=manifest_path,
        events_path=events_path,
        public_keys_path=public_keys_path,
        verification_report_path=verification_report_path,
        manifest_hash=_sha256_file(manifest_path),
        verification_result=verification_result,
    )


def write_legacy_ledger_export(
    *,
    vectors: Sequence[Mapping[str, Any]],
    export_dir: str | Path,
    allow_overwrite: bool = False,
) -> LegacyLedgerExportResult:
    """Write legacy-v0 integrity vectors and explicit limitation notes."""
    if not vectors:
        raise ValueError("at least one legacy vector is required")
    root = Path(export_dir)
    _prepare_export_dir(root, allow_overwrite=allow_overwrite)

    vector_paths: list[Path] = []
    for index, vector in enumerate(vectors, start=1):
        value = dict(vector)
        if value.get("profile") != "legacy-v0":
            raise ValueError(f"legacy vector profile unsupported: {value.get('profile')}")
        path = root / f"legacy_v0_vector_{index}.json"
        _write_json_atomic(path, value)
        vector_paths.append(path)

    limitations_path = root / "LIMITATIONS.txt"
    _write_text_atomic(
        limitations_path,
        "\n".join(
            [
                "Legacy-v0 ledger export is integrity-only.",
                "Origin authenticity, manifest completeness, online freshness, and truth are not verified.",
                *LEGACY_LIMITATIONS,
                "",
            ]
        ),
    )
    report = verify_export(root)
    _scan_export_safety(
        root, allowed_files={path.name for path in vector_paths} | {"LIMITATIONS.txt"}
    )
    return LegacyLedgerExportResult(
        export_dir=root,
        vector_paths=tuple(vector_paths),
        limitations_path=limitations_path,
        verification_result=str(report["result"]),
        limitations=LEGACY_LIMITATIONS,
    )


def public_key_record(
    *,
    key_id: str,
    actor_id: str,
    public_key: Ed25519PublicKey,
    permissions: Sequence[str],
    actor_type: str = "agent",
    environment: str = "test",
    valid_from: str = "2026-01-01T00:00:00Z",
    valid_until: str = "2027-01-01T00:00:00Z",
    hardware_backed: bool = False,
) -> dict[str, Any]:
    """Build a public key registry record for exported ledger verification."""
    return {
        "actor_id": actor_id,
        "actor_type": actor_type,
        "algorithm": "ed25519",
        "environment": environment,
        "hardware_backed": hardware_backed,
        "key_id": key_id,
        "permissions": list(permissions),
        "public_key": _public_key_b64url(public_key),
        "status": "active",
        "valid_from": valid_from,
        "valid_until": valid_until,
    }


def _manifest_document(
    *,
    events: Sequence[Mapping[str, Any]],
    event_hashes: Sequence[str],
    export_id: str,
    tenant_id: str,
    stream_id: str,
    created_by: str,
    created_at: str,
    purpose: str,
    environment: str,
    root: Path,
) -> dict[str, Any]:
    first = events[0]
    last = events[-1]
    return {
        "algorithms": {
            "event_hash": "sha256",
            "manifest_hash": "sha256",
            "merkle": "merkle-profile-v1",
            "signature": "ed25519",
        },
        "counts": {
            "erasure_tombstone_count": 0,
            "event_count": len(events),
            "redacted_event_count": 0,
        },
        "created_at": created_at,
        "created_by": created_by,
        "environment": environment,
        "export_id": export_id,
        "hashes": {
            "events_file_sha256": _sha256_file(root / "events.jsonl"),
            "first_event_hash": event_hashes[0],
            "key_events_file_sha256": _sha256_file(root / "key-events.jsonl"),
            "last_event_hash": event_hashes[-1],
            "merkle_root": _merkle_root_v1(event_hashes),
            "public_keys_file_sha256": _sha256_file(root / "public-keys.json"),
            "schema_file_sha256": _sha256_file(root / "schema.json"),
            "verification_profile_sha256": _sha256_file(root / "verification-profile.json"),
        },
        "limitations": [],
        "purpose": purpose,
        "range": {
            "first_recorded_at": first["recorded_at"],
            "first_sequence": first["sequence"],
            "last_recorded_at": last["recorded_at"],
            "last_sequence": last["sequence"],
        },
        "schema_version": PUBLIC_EXPORT_MANIFEST_VERSION,
        "stream_id": stream_id,
        "tenant_id": tenant_id,
    }


def _key_registry_document(
    *,
    tenant_id: str,
    public_keys: Sequence[Mapping[str, Any]],
    export_authority: ExportAuthority,
    generated_at: str,
) -> dict[str, Any]:
    keys = [dict(key) for key in public_keys]
    if not any(key.get("key_id") == export_authority.key_id for key in keys):
        keys.append(
            public_key_record(
                key_id=export_authority.key_id,
                actor_id=export_authority.actor_id,
                actor_type="export_authority",
                environment=export_authority.environment,
                public_key=export_authority.private_key.public_key(),
                permissions=["ledger.export"],
            )
        )
    return {
        "generated_at": generated_at,
        "keys": sorted(keys, key=lambda key: str(key["key_id"])),
        "schema_version": KEY_REGISTRY_VERSION,
        "tenant_id": tenant_id,
    }


def _schema_document() -> dict[str, str]:
    return {"profile": "public-v1-strict", "schema_version": EVENT_SCHEMA_VERSION}


def _verification_profile_document() -> dict[str, str]:
    return {
        "canonicalization": "canonical-json-v1",
        "merkle": "merkle-profile-v1",
        "profile": "public-v1-strict",
        "schema_version": VERIFICATION_PROFILE_VERSION,
    }


def _validate_public_events(
    events: Sequence[Mapping[str, Any]],
    *,
    tenant_id: str,
    stream_id: str,
) -> list[str]:
    previous_sequence: int | None = None
    previous_hash = "GENESIS"
    seen_event_ids: set[str] = set()
    seen_nonces: set[str] = set()
    event_hashes: list[str] = []
    for index, event in enumerate(events, start=1):
        missing = sorted(STRICT_REQUIRED_EVENT_FIELDS - event.keys())
        if missing:
            raise ValueError(f"event missing public-v1 fields at {index}: {','.join(missing)}")
        event_id = str(event["event_id"])
        nonce = str(event["nonce"])
        if event_id in seen_event_ids:
            raise ValueError(f"duplicate event_id before export: {event_id}")
        if nonce in seen_nonces:
            raise ValueError(f"duplicate nonce before export: {nonce}")
        seen_event_ids.add(event_id)
        seen_nonces.add(nonce)
        if event.get("tenant_id") != tenant_id:
            raise ValueError(f"event tenant mismatch: {event_id}")
        if event.get("stream_id") != stream_id:
            raise ValueError(f"event stream mismatch: {event_id}")
        if event.get("prev_hash") != previous_hash:
            raise ValueError(f"event chain break before export: {event_id}")
        sequence = event.get("sequence")
        if isinstance(sequence, bool) or not isinstance(sequence, int):
            raise ValueError(f"event sequence invalid: {event_id}")
        if previous_sequence is None and sequence != 1:
            raise ValueError(f"event sequence must start at 1: {event_id}")
        if previous_sequence is not None and sequence != previous_sequence + 1:
            raise ValueError(f"event sequence gap: {event_id}")
        detail = event.get("detail")
        if isinstance(detail, Mapping) and any(
            field in detail for field in ("content", "payload", "plaintext", "fact_content")
        ):
            raise ValueError(f"event contains inline fact payload: {event_id}")
        actual_hash = _event_hash(event)
        if actual_hash != event.get("hash"):
            raise ValueError(f"event hash mismatch before export: {event_id}")
        event_hashes.append(actual_hash)
        previous_sequence = sequence
        previous_hash = actual_hash
    return event_hashes


def _validate_public_key_records(keys: Sequence[Mapping[str, Any]]) -> None:
    seen: set[str] = set()
    for key in keys:
        key_id = key.get("key_id")
        if not isinstance(key_id, str) or not key_id:
            raise ValueError("public key record missing key_id")
        if key_id in seen:
            raise ValueError(f"duplicate public key id: {key_id}")
        seen.add(key_id)
        if key.get("algorithm") != "ed25519":
            raise ValueError(f"public key algorithm unsupported: {key_id}")
        if not isinstance(key.get("public_key"), str):
            raise ValueError(f"public key missing material: {key_id}")
        if not isinstance(key.get("permissions"), list):
            raise ValueError(f"public key permissions missing: {key_id}")


def _prepare_export_dir(root: Path, *, allow_overwrite: bool) -> None:
    if root.exists() and any(root.iterdir()) and not allow_overwrite:
        raise FileExistsError(f"export directory is not empty: {root}")
    root.mkdir(parents=True, exist_ok=True)


def _assert_no_private_material(value: Any) -> None:
    text = _canonical_public_json(value).lower()
    for token in FORBIDDEN_EXPORT_TOKENS:
        if token in text:
            raise ValueError(f"export contains forbidden token: {token}")


def _scan_export_safety(root: Path, *, allowed_files: set[str] | None = None) -> None:
    allowed = allowed_files or set(PUBLIC_EXPORT_FILES)
    for path in root.iterdir():
        if not path.is_file():
            raise ValueError(f"export contains non-file entry: {path.name}")
        if path.name not in allowed:
            raise ValueError(f"export contains unexpected file: {path.name}")
        if path.suffix in EXECUTABLE_SUFFIXES:
            raise ValueError(f"export contains executable-like file: {path.name}")
        mode = path.stat().st_mode
        if mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
            raise ValueError(f"export contains executable file: {path.name}")
        _assert_no_private_material(path.read_text(encoding="utf-8"))


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    _write_text_atomic(path, _canonical_public_json(value))


def _write_text_atomic(path: Path, value: str) -> None:
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(value, encoding="utf-8")
    os.replace(tmp_path, path)


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _public_key_b64url(public_key: Ed25519PublicKey) -> str:
    return _b64url_encode(public_key.public_bytes(Encoding.Raw, PublicFormat.Raw))


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
