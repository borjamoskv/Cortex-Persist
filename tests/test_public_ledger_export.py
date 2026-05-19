from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

from cortex.cli import cli
from cortex.ledger.public_export import (
    ExportAuthority,
    public_key_record,
    write_legacy_ledger_export,
    write_public_ledger_export,
)
from cortex.ledger.public_verifier import verify_export

TENANT_ID = "tenant-acme"
STREAM_ID = "tenant:acme:ledger:primary"
ACTOR_ID = "agent-risk-01"
ACTOR_KEY_ID = "ed25519:agent-risk-01:test-export-001"
EXPORT_KEY_ID = "ed25519:export-authority:test-export-001"
CREATED_AT = "2026-02-03T10:15:30Z"


def test_write_public_ledger_export_package_with_verification_report(tmp_path: Path) -> None:
    actor_private_key = Ed25519PrivateKey.generate()
    export_private_key = Ed25519PrivateKey.generate()
    first = _signed_event(actor_private_key, sequence=1, prev_hash="GENESIS")
    second = _signed_event(actor_private_key, sequence=2, prev_hash=first["hash"])
    export_dir = tmp_path / "forensic-export"

    result = write_public_ledger_export(
        events=[first, second],
        export_dir=export_dir,
        public_keys=[
            public_key_record(
                key_id=ACTOR_KEY_ID,
                actor_id=ACTOR_ID,
                public_key=actor_private_key.public_key(),
                permissions=["fact.store"],
            )
        ],
        export_authority=ExportAuthority(
            key_id=EXPORT_KEY_ID,
            actor_id="export-authority-01",
            private_key=export_private_key,
        ),
        export_id="export-2026-02-03-001",
        tenant_id=TENANT_ID,
        stream_id=STREAM_ID,
        created_at=CREATED_AT,
        include_verification_report=True,
    )

    expected_files = {
        "events.jsonl",
        "key-events.jsonl",
        "manifest.json",
        "public-keys.json",
        "schema.json",
        "verification-profile.json",
        "verification-report.json",
    }
    assert expected_files == {path.name for path in export_dir.iterdir()}
    assert not (export_dir / "facts.jsonl").exists()
    assert result.verification_report_path == export_dir / "verification-report.json"
    assert result.verification_result == "VALID_FULL_STRICT"
    assert result.manifest_hash == _sha256_file(export_dir / "manifest.json")

    report = verify_export(export_dir)
    assert report["result"] == "VALID_FULL_STRICT"
    assert report["guarantees"]["integrity_verified"] is True
    assert report["guarantees"]["origin_authenticity_verified"] is True
    assert report["guarantees"]["authority_verified"] is True
    assert report["guarantees"]["completeness_verified"] is True
    assert report["guarantees"]["truth_verified"] is False
    assert report == _load_json(export_dir / "verification-report.json")

    manifest = _load_json(export_dir / "manifest.json")
    public_keys = _load_json(export_dir / "public-keys.json")
    assert manifest["signature"]["key_id"] == EXPORT_KEY_ID
    assert manifest["hashes"]["events_file_sha256"] == _sha256_file(export_dir / "events.jsonl")
    assert manifest["hashes"]["public_keys_file_sha256"] == _sha256_file(
        export_dir / "public-keys.json"
    )
    assert {key["key_id"] for key in public_keys["keys"]} == {ACTOR_KEY_ID, EXPORT_KEY_ID}
    assert manifest["counts"]["event_count"] == 2
    assert manifest["range"]["first_sequence"] == 1
    assert manifest["range"]["last_sequence"] == 2


def test_export_tail_truncation_causes_manifest_mismatch(tmp_path: Path) -> None:
    export_dir = _write_valid_export(tmp_path)
    lines = (export_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    (export_dir / "events.jsonl").write_text(lines[0] + "\n", encoding="utf-8")

    report = verify_export(export_dir)

    assert report["result"] == "INVALID"
    assert "manifest_file_hash_mismatch:events_file_sha256" in report["errors"]
    assert "manifest_event_count_mismatch" in report["errors"]


def test_export_detail_tampering_causes_hash_mismatch(tmp_path: Path) -> None:
    export_dir = _write_valid_export(tmp_path)
    events = [
        json.loads(line)
        for line in (export_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    events[0]["detail"]["fact_type"] = "tampered"
    (export_dir / "events.jsonl").write_text(
        "".join(_canonical_json(event) + "\n" for event in events),
        encoding="utf-8",
    )

    report = verify_export(export_dir)

    assert report["result"] == "INVALID"
    assert "event_hash_mismatch:evt_01HXEXPORT0000000000000001" in report["errors"]


def test_export_missing_manifest_cannot_be_full_strict(tmp_path: Path) -> None:
    export_dir = _write_valid_export(tmp_path)
    (export_dir / "manifest.json").unlink()

    report = verify_export(export_dir)

    assert report["result"] == "VALID_WITH_LIMITATIONS"
    assert report["guarantees"]["completeness_verified"] is False
    assert report["guarantees"]["truth_verified"] is False


def test_export_rejects_inline_fact_payload_and_private_material(tmp_path: Path) -> None:
    actor_private_key = Ed25519PrivateKey.generate()
    export_private_key = Ed25519PrivateKey.generate()
    event = _signed_event(actor_private_key, sequence=1, prev_hash="GENESIS")
    event["detail"] = dict(event["detail"])
    event["detail"]["payload"] = "plaintext fact body"

    with pytest.raises(ValueError, match="inline fact payload"):
        write_public_ledger_export(
            events=[event],
            export_dir=tmp_path / "inline-payload",
            public_keys=[
                public_key_record(
                    key_id=ACTOR_KEY_ID,
                    actor_id=ACTOR_ID,
                    public_key=actor_private_key.public_key(),
                    permissions=["fact.store"],
                )
            ],
            export_authority=ExportAuthority(
                key_id=EXPORT_KEY_ID,
                actor_id="export-authority-01",
                private_key=export_private_key,
            ),
            export_id="export-2026-02-03-001",
            tenant_id=TENANT_ID,
            stream_id=STREAM_ID,
            created_at=CREATED_AT,
        )

    event = _signed_event(actor_private_key, sequence=1, prev_hash="GENESIS")
    with pytest.raises(ValueError, match="forbidden token: private_key"):
        write_public_ledger_export(
            events=[event],
            export_dir=tmp_path / "private-material",
            public_keys=[
                {
                    **public_key_record(
                        key_id=ACTOR_KEY_ID,
                        actor_id=ACTOR_ID,
                        public_key=actor_private_key.public_key(),
                        permissions=["fact.store"],
                    ),
                    "private_key": "never export this",
                }
            ],
            export_authority=ExportAuthority(
                key_id=EXPORT_KEY_ID,
                actor_id="export-authority-01",
                private_key=export_private_key,
            ),
            export_id="export-2026-02-03-001",
            tenant_id=TENANT_ID,
            stream_id=STREAM_ID,
            created_at=CREATED_AT,
        )


def test_export_contains_no_private_keys_secrets_or_executables(tmp_path: Path) -> None:
    export_dir = _write_valid_export(tmp_path)

    for path in export_dir.iterdir():
        assert path.suffix in {".json", ".jsonl"}
        assert not os.access(path, os.X_OK)
        text = path.read_text(encoding="utf-8").lower()
        assert "private_key" not in text
        assert "begin private key" not in text
        assert "secret_key" not in text


def test_legacy_export_is_marked_integrity_only(tmp_path: Path) -> None:
    vector = _load_json(Path("tests/fixtures/ledger_verifier/legacy_v0_vector_1.json"))
    export_dir = tmp_path / "legacy-export"

    result = write_legacy_ledger_export(vectors=[vector], export_dir=export_dir)

    assert result.verification_result == "VALID_INTEGRITY_ONLY"
    assert result.limitations == (
        "legacy_v0_integrity_only",
        "origin_authenticity_not_verified",
        "manifest_completeness_not_available",
    )
    assert "integrity-only" in result.limitations_path.read_text(encoding="utf-8")
    assert verify_export(export_dir)["result"] == "VALID_INTEGRITY_ONLY"


def test_export_ledger_cli_writes_verifiable_package(tmp_path: Path) -> None:
    actor_private_key = Ed25519PrivateKey.generate()
    export_private_key = Ed25519PrivateKey.generate()
    event = _signed_event(actor_private_key, sequence=1, prev_hash="GENESIS")
    events_path = tmp_path / "events.jsonl"
    keys_path = tmp_path / "public-keys.json"
    seed_path = tmp_path / "export-authority.seed"
    export_dir = tmp_path / "cli-export"
    events_path.write_text(_canonical_json(event) + "\n", encoding="utf-8")
    keys_path.write_text(
        _canonical_json(
            {
                "keys": [
                    public_key_record(
                        key_id=ACTOR_KEY_ID,
                        actor_id=ACTOR_ID,
                        public_key=actor_private_key.public_key(),
                        permissions=["fact.store"],
                    )
                ]
            }
        ),
        encoding="utf-8",
    )
    seed_path.write_text(_private_seed_b64url(export_private_key), encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "export-ledger",
            str(events_path),
            str(export_dir),
            "--public-keys",
            str(keys_path),
            "--export-id",
            "export-2026-02-03-001",
            "--tenant-id",
            TENANT_ID,
            "--stream-id",
            STREAM_ID,
            "--export-authority-key-id",
            EXPORT_KEY_ID,
            "--export-authority-actor-id",
            "export-authority-01",
            "--export-authority-private-key-seed",
            str(seed_path),
            "--created-at",
            CREATED_AT,
            "--include-verification-report",
        ],
    )

    assert result.exit_code == 0, result.output
    summary = json.loads(result.output)
    assert summary["verification_result"] == "VALID_FULL_STRICT"
    assert verify_export(export_dir)["result"] == "VALID_FULL_STRICT"
    assert not (export_dir / "facts.jsonl").exists()


def _write_valid_export(tmp_path: Path) -> Path:
    actor_private_key = Ed25519PrivateKey.generate()
    export_private_key = Ed25519PrivateKey.generate()
    first = _signed_event(actor_private_key, sequence=1, prev_hash="GENESIS")
    second = _signed_event(actor_private_key, sequence=2, prev_hash=first["hash"])
    export_dir = tmp_path / "forensic-export"
    write_public_ledger_export(
        events=[first, second],
        export_dir=export_dir,
        public_keys=[
            public_key_record(
                key_id=ACTOR_KEY_ID,
                actor_id=ACTOR_ID,
                public_key=actor_private_key.public_key(),
                permissions=["fact.store"],
            )
        ],
        export_authority=ExportAuthority(
            key_id=EXPORT_KEY_ID,
            actor_id="export-authority-01",
            private_key=export_private_key,
        ),
        export_id="export-2026-02-03-001",
        tenant_id=TENANT_ID,
        stream_id=STREAM_ID,
        created_at=CREATED_AT,
        include_verification_report=True,
    )
    return export_dir


def _signed_event(
    private_key: Ed25519PrivateKey, *, sequence: int, prev_hash: str
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "action": "fact.store",
        "actor_id": ACTOR_ID,
        "actor_key_id": ACTOR_KEY_ID,
        "detail": {
            "fact_type": "risk_signal",
            "payload_ref": f"facts/tenant-acme/fact-{sequence:03d}.enc.json",
            "subject_ref": "subject:hmac-sha256:01HX",
        },
        "event_id": f"evt_01HXEXPORT000000000000000{sequence}",
        "hash_alg": "sha256",
        "issued_at": CREATED_AT,
        "nonce": f"nonce_01HXEXPORT000000000000000{sequence}",
        "prev_hash": prev_hash,
        "project": "cortex-persist",
        "recorded_at": CREATED_AT,
        "schema_version": "cortex-ledger-event-v1",
        "sequence": sequence,
        "signature_alg": "ed25519",
        "stream_id": STREAM_ID,
        "target": f"fact:{sequence:03d}",
        "tenant_id": TENANT_ID,
    }
    event["hash"] = _event_hash(event)
    event["origin_signature"] = _b64url_encode(
        private_key.sign(_canonical_json(event).encode("utf-8"))
    )
    return event


def _event_hash(event: dict[str, Any]) -> str:
    scope = dict(event)
    scope.pop("hash", None)
    scope.pop("origin_signature", None)
    return hashlib.sha256(_canonical_json(scope).encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _private_seed_b64url(private_key: Ed25519PrivateKey) -> str:
    seed = private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    return _b64url_encode(seed)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value
