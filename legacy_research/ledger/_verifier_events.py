# [C5-REAL] Exergy-Maximized
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from cryptography.exceptions import InvalidSignature

from legacy_research.ledger.public_verifier_utils import (
    PublicVerifierError,
    _event_hash,
    _event_signature_scope,
    _has_error_prefix,
    _parse_utc,
    _require_int,
    _require_str,
    _string_list,
    _verify_ed25519,
)

if TYPE_CHECKING:
    from legacy_research.ledger._types import PublicVerifierProtocol as _PublicLedgerVerifier

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


def verify_events(verifier: _PublicLedgerVerifier) -> None:
    seen_event_ids: set[str] = set()
    seen_nonces: set[str] = set()
    previous_hash = "GENESIS"
    previous_sequence: int | None = None
    integrity_ok = bool(verifier.events)
    origin_ok = bool(verifier.events) and bool(verifier.key_index)
    authority_ok = bool(verifier.events) and bool(verifier.key_index)
    replay_ok = bool(verifier.events)
    temporal_ok = bool(verifier.events)

    for index, event in enumerate(verifier.events, start=1):
        (i_ok, o_ok, a_ok, r_ok, t_ok, previous_sequence, previous_hash) = _verify_single_event(
            verifier,
            event,
            index,
            seen_event_ids,
            seen_nonces,
            previous_sequence,
            previous_hash,
        )
        integrity_ok = integrity_ok and i_ok
        origin_ok = origin_ok and o_ok
        authority_ok = authority_ok and a_ok
        replay_ok = replay_ok and r_ok
        temporal_ok = temporal_ok and t_ok

    verifier.guarantees["integrity_verified"] = integrity_ok and not _has_error_prefix(
        verifier.errors,
        ("event_hash_", "event_chain_", "event_missing_", "event_unsupported_hash"),
    )
    verifier.guarantees["origin_authenticity_verified"] = origin_ok
    verifier.guarantees["authority_verified"] = authority_ok
    verifier.guarantees["replay_consistency_verified"] = replay_ok
    verifier.guarantees["temporal_consistency_verified"] = temporal_ok


def _verify_single_event(
    verifier: _PublicLedgerVerifier,
    event: dict[str, Any],
    index: int,
    seen_event_ids: set[str],
    seen_nonces: set[str],
    previous_sequence: int | None,
    previous_hash: str,
) -> tuple[bool, bool, bool, bool, bool, int, str]:
    integrity_ok = True
    origin_ok = True
    authority_ok = True
    replay_ok = True
    temporal_ok = True

    missing = sorted(STRICT_REQUIRED_EVENT_FIELDS - event.keys())
    if missing:
        verifier.errors.append(f"event_missing_required_fields:{index}:{','.join(missing)}")
        return False, False, False, False, False, previous_sequence or 0, previous_hash

    if event.get("hash_alg") != "sha256":
        verifier.errors.append(f"event_unsupported_hash_alg:{index}:{event.get('hash_alg')}")
        integrity_ok = False
    if event.get("signature_alg") != "ed25519":
        verifier.errors.append(
            f"event_unsupported_signature_alg:{index}:{event.get('signature_alg')}"
        )
        origin_ok = False

    event_id = _require_str(event, "event_id", index, verifier.errors)
    nonce = _require_str(event, "nonce", index, verifier.errors)
    sequence = _require_int(event, "sequence", index, verifier.errors)
    if event_id in seen_event_ids:
        verifier.errors.append(f"event_replay_duplicate_event_id:{event_id}")
        replay_ok = False
    seen_event_ids.add(event_id)
    if nonce in seen_nonces:
        verifier.errors.append(f"event_replay_duplicate_nonce:{nonce}")
        replay_ok = False
    seen_nonces.add(nonce)

    if previous_sequence is None and sequence != 1:
        verifier.errors.append(f"event_sequence_start_invalid:{index}:expected:1")
        replay_ok = False
    if previous_sequence is not None and sequence != previous_sequence + 1:
        verifier.errors.append(f"event_sequence_gap:{index}:expected:{previous_sequence + 1}")
        replay_ok = False
    previous_sequence = sequence

    prev_hash = _require_str(event, "prev_hash", index, verifier.errors)
    if prev_hash != previous_hash:
        verifier.errors.append(f"event_chain_break:{index}:expected:{previous_hash}")
        integrity_ok = False

    computed_hash = _event_hash(event)
    expected_hash = _require_str(event, "hash", index, verifier.errors)
    verifier.event_hashes.append(expected_hash)
    if computed_hash != expected_hash:
        verifier.errors.append(f"event_hash_mismatch:{event_id}")
        integrity_ok = False
    previous_hash = expected_hash

    temporal_ok = temporal_ok and _verify_event_time(verifier, event, index)
    key = verifier.key_index.get(str(event.get("actor_key_id")))
    if key is None:
        verifier.errors.append(f"event_actor_key_missing:{event_id}")
        origin_ok = False
        authority_ok = False
        temporal_ok = False
        return (
            integrity_ok,
            origin_ok,
            authority_ok,
            replay_ok,
            temporal_ok,
            previous_sequence,
            previous_hash,
        )

    if key.get("actor_id") != event.get("actor_id"):
        verifier.errors.append(f"event_actor_key_actor_mismatch:{event_id}")
        authority_ok = False
    if key.get("algorithm") != "ed25519":
        verifier.errors.append(f"event_actor_key_unsupported_algorithm:{event_id}")
        origin_ok = False
    if event.get("action") not in _string_list(key.get("permissions")):
        verifier.errors.append(f"event_actor_key_permission_denied:{event_id}")
        authority_ok = False
    if not _key_valid_for_event(verifier, key, event, index):
        temporal_ok = False
        authority_ok = False

    try:
        _verify_ed25519(
            _event_signature_scope(event),
            str(event["origin_signature"]),
            str(key["public_key"]),
        )
    except (InvalidSignature, PublicVerifierError, KeyError, TypeError, ValueError) as exc:
        verifier.errors.append(
            f"event_origin_signature_invalid:{event_id}:{exc.__class__.__name__}"
        )
        origin_ok = False

    return (
        integrity_ok,
        origin_ok,
        authority_ok,
        replay_ok,
        temporal_ok,
        previous_sequence,
        previous_hash,
    )


def _verify_event_time(
    verifier: _PublicLedgerVerifier, event: Mapping[str, Any], index: int
) -> bool:
    try:
        issued_at = _parse_utc(str(event["issued_at"]))
        recorded_at = _parse_utc(str(event["recorded_at"]))
    except (KeyError, PublicVerifierError) as exc:
        verifier.errors.append(f"event_timestamp_invalid:{index}:{exc.__class__.__name__}")
        return False
    if recorded_at < issued_at:
        verifier.errors.append(f"event_recorded_before_issued:{index}")
        return False
    return True


def _key_valid_for_event(
    verifier: _PublicLedgerVerifier,
    key: Mapping[str, Any],
    event: Mapping[str, Any],
    index: int,
) -> bool:
    status = key.get("status")
    if status not in {"active", "rotated", "revoked"}:
        verifier.errors.append(f"event_key_not_active:{index}")
        return False
    if status == "revoked" and not key.get("valid_until"):
        verifier.errors.append(f"event_key_revoked_without_valid_until:{index}")
        return False
    try:
        issued_at = _parse_utc(str(event["issued_at"]))
        valid_from = _parse_utc(str(key["valid_from"]))
        valid_until = _parse_utc(str(key["valid_until"]))
    except (KeyError, PublicVerifierError) as exc:
        verifier.errors.append(f"event_key_validity_invalid:{index}:{exc.__class__.__name__}")
        return False
    if not valid_from <= issued_at <= valid_until:
        verifier.errors.append(f"event_key_outside_validity:{index}")
        return False
    return True
