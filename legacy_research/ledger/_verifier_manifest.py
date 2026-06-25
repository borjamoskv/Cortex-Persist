# [C5-REAL] Exergy-Maximized
from __future__ import annotations

from typing import TYPE_CHECKING

from cryptography.exceptions import InvalidSignature

from legacy_research.ledger.public_verifier_utils import (
    PublicVerifierError,
    _manifest_signature_scope,
    _merkle_root_v1,
    _sha256_file,
    _string_list,
    _verify_ed25519,
)

if TYPE_CHECKING:
    from legacy_research.ledger._types import PublicVerifierProtocol as _PublicLedgerVerifier


def verify_manifest(verifier: _PublicLedgerVerifier) -> None:
    if verifier.manifest is None:
        return

    manifest_signature_ok = _verify_manifest_signature(verifier)
    file_hashes_ok = _verify_manifest_file_hashes(verifier)
    range_ok = _verify_manifest_range(verifier)
    merkle_ok = _verify_manifest_merkle(verifier)
    counts_ok = _verify_manifest_counts(verifier)
    manifest_scope_ok = _verify_manifest_scope(verifier)

    verifier.guarantees["completeness_verified"] = (
        manifest_signature_ok
        and file_hashes_ok
        and range_ok
        and merkle_ok
        and counts_ok
        and manifest_scope_ok
        and verifier.guarantees["integrity_verified"]
    )


def _verify_manifest_signature(verifier: _PublicLedgerVerifier) -> bool:
    manifest = verifier.manifest
    if manifest is None:
        verifier.errors.append("manifest_missing")
        return False
    signature = manifest.get("signature")
    if not isinstance(signature, dict):
        verifier.errors.append("manifest_signature_missing")
        return False
    key_id = signature.get("key_id")
    value = signature.get("value")
    key = verifier.key_index.get(str(key_id))
    if key is None:
        verifier.errors.append(f"manifest_signature_key_missing:{key_id}")
        return False
    if "ledger.export" not in _string_list(key.get("permissions")):
        verifier.errors.append(f"manifest_signature_permission_denied:{key_id}")
        return False
    try:
        _verify_ed25519(
            _manifest_signature_scope(manifest),
            str(value),
            str(key["public_key"]),
        )
    except (InvalidSignature, PublicVerifierError, KeyError, TypeError, ValueError) as exc:
        verifier.errors.append(f"manifest_signature_invalid:{exc.__class__.__name__}")
        return False
    return True


def _verify_manifest_file_hashes(verifier: _PublicLedgerVerifier) -> bool:
    manifest = verifier.manifest
    if manifest is None:
        verifier.errors.append("manifest_missing")
        return False
    hashes = manifest.get("hashes")
    if not isinstance(hashes, dict):
        verifier.errors.append("manifest_hashes_missing")
        return False
    expected = {
        "events_file_sha256": verifier.paths.events_path,
        "schema_file_sha256": verifier.paths.schema_path,
        "public_keys_file_sha256": verifier.paths.public_keys_path,
        "key_events_file_sha256": verifier.paths.key_events_path,
        "verification_profile_sha256": verifier.paths.verification_profile_path,
    }
    ok = True
    for field, path in expected.items():
        expected_hash = hashes.get(field)
        if not isinstance(expected_hash, str):
            verifier.errors.append(f"manifest_hash_missing:{field}")
            ok = False
            continue
        if not path.exists():
            verifier.errors.append(f"manifest_file_missing:{path.name}")
            ok = False
            continue
        if _sha256_file(path) != expected_hash:
            verifier.errors.append(f"manifest_file_hash_mismatch:{field}")
            ok = False
    return ok


def _verify_manifest_range(verifier: _PublicLedgerVerifier) -> bool:
    manifest = verifier.manifest
    if manifest is None:
        verifier.errors.append("manifest_missing")
        return False
    if not verifier.events:
        verifier.errors.append("manifest_range_without_events")
        return False
    event_range = manifest.get("range")
    if not isinstance(event_range, dict):
        verifier.errors.append("manifest_range_missing")
        return False
    first = verifier.events[0]
    last = verifier.events[-1]
    expected = {
        "first_sequence": first.get("sequence"),
        "last_sequence": last.get("sequence"),
        "first_recorded_at": first.get("recorded_at"),
        "last_recorded_at": last.get("recorded_at"),
    }
    ok = True
    for field, expected_value in expected.items():
        if event_range.get(field) != expected_value:
            verifier.errors.append(f"manifest_range_mismatch:{field}")
            ok = False
    return ok


def _verify_manifest_merkle(verifier: _PublicLedgerVerifier) -> bool:
    manifest = verifier.manifest
    if manifest is None:
        verifier.errors.append("manifest_missing")
        return False
    hashes = manifest.get("hashes")
    if not isinstance(hashes, dict):
        return False
    expected_root = hashes.get("merkle_root")
    if not isinstance(expected_root, str):
        verifier.errors.append("manifest_merkle_root_missing")
        return False
    if _merkle_root_v1(verifier.event_hashes) != expected_root:
        verifier.errors.append("manifest_merkle_root_mismatch")
        return False
    return True


def _verify_manifest_counts(verifier: _PublicLedgerVerifier) -> bool:
    manifest = verifier.manifest
    if manifest is None:
        verifier.errors.append("manifest_missing")
        return False
    counts = manifest.get("counts")
    if not isinstance(counts, dict):
        verifier.errors.append("manifest_counts_missing")
        return False
    if counts.get("event_count") != len(verifier.events):
        verifier.errors.append("manifest_event_count_mismatch")
        return False
    return True


def _verify_manifest_scope(verifier: _PublicLedgerVerifier) -> bool:
    manifest = verifier.manifest
    if manifest is None:
        verifier.errors.append("manifest_missing")
        return False
    stream_id = manifest.get("stream_id")
    tenant_id = manifest.get("tenant_id")
    ok = True
    for event in verifier.events:
        if event.get("stream_id") != stream_id:
            verifier.errors.append(f"manifest_stream_mismatch:{event.get('event_id')}")
            ok = False
        if event.get("tenant_id") != tenant_id:
            verifier.errors.append(f"manifest_tenant_mismatch:{event.get('event_id')}")
            ok = False
    return ok


def manifest_export_authority_ok(verifier: _PublicLedgerVerifier) -> bool:
    manifest = verifier.manifest
    if manifest is None:
        return False
    signature = manifest.get("signature")
    if not isinstance(signature, dict):
        return False
    key = verifier.key_index.get(str(signature.get("key_id")))
    return key is not None and "ledger.export" in _string_list(key.get("permissions"))
