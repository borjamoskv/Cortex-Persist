from __future__ import annotations

import base64
import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from cortex.ledger.pii import LedgerPIIError, validate_no_direct_identifiers
from cortex.ledger.public_verifier import verify_export


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
    include_verification_report: bool = False,
) -> LedgerExportResult:
    """Write a signed public ledger export package without exporting fact payloads."""
    if not events:
        raise ValueError("at least one ledger event is required")
    root = Path(export_dir)
    root.mkdir(parents=True, exist_ok=True)

    event_objects = [dict(event) for event in events]
    _validate_event_package_scope(event_objects, tenant_id=tenant_id, stream_id=stream_id)

    events_path = root / "events.jsonl"
    public_keys_path = root / "public-keys.json"
    key_events_path = root / "key-events.jsonl"
    schema_path = root / "schema.json"
    verification_profile_path = root / "verification-profile.json"
    manifest_path = root / "manifest.json"
    verification_report_path = root / "verification-report.json"

    _write_text_atomic(
        events_path,
        "".join(_canonical_json(event) + "\n" for event in event_objects),
    )
    _write_text_atomic(key_events_path, "")
    _write_json_atomic(schema_path, _schema_document())
    _write_json_atomic(verification_profile_path, _verification_profile_document())
    _write_json_atomic(
        public_keys_path,
        _key_registry_document(
            tenant_id=tenant_id,
            public_keys=public_keys,
            export_authority=export_authority,
            generated_at=created_at or _utc_now(),
        ),
    )

    manifest_without_signature = _manifest_document(
        events=event_objects,
        export_id=export_id,
        tenant_id=tenant_id,
        stream_id=stream_id,
        created_by=export_authority.actor_id,
        created_at=created_at or _utc_now(),
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
                _canonical_json(manifest_without_signature).encode("utf-8")
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

    return LedgerExportResult(
        export_dir=root,
        manifest_path=manifest_path,
        events_path=events_path,
        public_keys_path=public_keys_path,
        verification_report_path=verification_report_path,
        manifest_hash=_sha256_file(manifest_path),
        verification_result=verification_result,
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
    export_id: str,
    tenant_id: str,
    stream_id: str,
    created_by: str,
    created_at: str,
    purpose: str,
    environment: str,
    root: Path,
) -> dict[str, Any]:
    hashes = [str(event["hash"]) for event in events]
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
            "first_event_hash": hashes[0],
            "key_events_file_sha256": _sha256_file(root / "key-events.jsonl"),
            "last_event_hash": hashes[-1],
            "merkle_root": _merkle_root_v1(hashes),
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
        "schema_version": "cortex-forensic-export-manifest-v1",
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
        "schema_version": "cortex-key-registry-v1",
        "tenant_id": tenant_id,
    }


def _schema_document() -> dict[str, str]:
    return {"profile": "public-v1-strict", "schema_version": "cortex-ledger-event-schema-v1"}


def _verification_profile_document() -> dict[str, str]:
    return {
        "canonicalization": "canonical-json-v1",
        "merkle": "merkle-profile-v1",
        "profile": "public-v1-strict",
        "schema_version": "cortex-verification-profile-v1",
    }


def _validate_event_package_scope(
    events: Sequence[Mapping[str, Any]],
    *,
    tenant_id: str,
    stream_id: str,
) -> None:
    previous_sequence: int | None = None
    previous_hash = "GENESIS"
    for event in events:
        if event.get("tenant_id") != tenant_id:
            raise ValueError(f"event tenant mismatch: {event.get('event_id')}")
        if event.get("stream_id") != stream_id:
            raise ValueError(f"event stream mismatch: {event.get('event_id')}")
        try:
            validate_no_direct_identifiers(event, path="event")
        except LedgerPIIError as exc:
            raise ValueError(f"event contains direct identifier: {exc}") from exc
        detail = event.get("detail")
        if isinstance(detail, Mapping) and any(
            field in detail for field in ("content", "payload", "plaintext", "fact_content")
        ):
            raise ValueError(f"event contains inline fact payload: {event.get('event_id')}")
        if event.get("prev_hash") != previous_hash:
            raise ValueError(f"event chain break before export: {event.get('event_id')}")
        sequence = event.get("sequence")
        if not isinstance(sequence, int):
            raise ValueError(f"event sequence invalid: {event.get('event_id')}")
        if previous_sequence is not None and sequence != previous_sequence + 1:
            raise ValueError(f"event sequence gap: {event.get('event_id')}")
        previous_sequence = sequence
        previous_hash = str(event.get("hash"))


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    _write_text_atomic(path, _canonical_json(value))


def _write_text_atomic(path: Path, value: str) -> None:
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(value, encoding="utf-8")
    os.replace(tmp_path, path)


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _public_key_b64url(public_key: Ed25519PublicKey) -> str:
    return _b64url_encode(public_key.public_bytes(Encoding.Raw, PublicFormat.Raw))


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


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
