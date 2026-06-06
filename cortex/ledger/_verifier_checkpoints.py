import logging
logger = logging.getLogger(__name__)
# [C5-REAL] Exergy-Maximized
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from cortex.ledger.public_verifier_utils import (
    _b64url_decode,
    _event_hash,
    _merkle_root_v1,
    _parse_utc,
    _string_list,
)

if TYPE_CHECKING:
    from cortex.ledger._types import PublicVerifierProtocol as _PublicLedgerVerifier


def verify_checkpoints(verifier: _PublicLedgerVerifier) -> None:
    if not verifier.checkpoints:
        return

    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric import mldsa
    except ImportError:
        verifier.errors.append("mldsa_unsupported_by_cryptography")
        return

    all_ok = True
    for index, cp in enumerate(verifier.checkpoints, start=1):
        if not _verify_single_checkpoint(verifier, index, cp, mldsa, InvalidSignature):
            all_ok = False

    if all_ok:
        verifier.guarantees["truth_verified"] = True


def _verify_single_checkpoint(
    verifier: _PublicLedgerVerifier, index: int, cp: dict, mldsa: Any, InvalidSignature: Any
) -> bool:
    required = {
        "root_hash",
        "start_event_id",
        "end_event_id",
        "event_count",
        "mldsa_signature",
        "mldsa_public_key",
    }
    missing = sorted(required - cp.keys())
    if missing:
        verifier.errors.append(f"checkpoint_missing_required_fields:{index}:{','.join(missing)}")
        return False

    root_hash = cp["root_hash"]
    start_ev = cp["start_event_id"]
    end_ev = cp["end_event_id"]
    count = cp["event_count"]
    sig_hex = cp["mldsa_signature"]
    pub_hex = cp["mldsa_public_key"]

    try:
        cp_pubkey_bytes = bytes.fromhex(pub_hex)
    except ValueError:
        verifier.errors.append(f"checkpoint_public_key_invalid_hex:{index}")
        return False

    matching_key = None
    if verifier.key_registry and isinstance(verifier.key_registry.get("keys"), list):
        for key_record in verifier.key_registry["keys"]:
            if not isinstance(key_record, dict):
                continue
            reg_pub_b64 = key_record.get("public_key")
            if not isinstance(reg_pub_b64, str):
                continue
            try:
                reg_pub_bytes = _b64url_decode(reg_pub_b64)
            except Exception as e:
                logger.debug("Failed to decode public key in key record %s: %s", reg_pub_b64, e)  # pyright: ignore[reportUndefinedVariable]
                continue
            if reg_pub_bytes == cp_pubkey_bytes:
                matching_key = key_record
                break

    if matching_key is None:
        verifier.errors.append(f"checkpoint_key_not_found:{index}:{pub_hex}")
        return False

    status = matching_key.get("status")
    if status not in {"active", "rotated", "revoked"}:
        verifier.errors.append(f"checkpoint_key_not_active:{index}")
        return False
    if status == "revoked" and not matching_key.get("valid_until"):
        verifier.errors.append(f"checkpoint_key_revoked_without_valid_until:{index}")
        return False

    if verifier.manifest:
        try:
            created_at = _parse_utc(str(verifier.manifest.get("created_at")))
            valid_from = _parse_utc(str(matching_key["valid_from"]))
            valid_until = _parse_utc(str(matching_key["valid_until"]))
            if not valid_from <= created_at <= valid_until:
                verifier.errors.append(f"checkpoint_key_outside_validity:{index}")
                return False
        except Exception as e:
            verifier.errors.append(f"checkpoint_validity_parse_error:{index}:{e}")
            return False

    permissions = _string_list(matching_key.get("permissions"))
    if not any(p in permissions for p in ("ledger.checkpoint", "ledger.export", "ledger.write")):
        verifier.errors.append(f"checkpoint_key_missing_permission:{index}")
        return False

    try:
        sig_bytes = bytes.fromhex(sig_hex)
    except ValueError:
        verifier.errors.append(f"checkpoint_signature_invalid_hex:{index}")
        return False

    try:
        length = len(cp_pubkey_bytes)
        if length == 1312:
            pubkey = mldsa.MLDSA44PublicKey.from_public_bytes(cp_pubkey_bytes)
        elif length == 1952:
            pubkey = mldsa.MLDSA65PublicKey.from_public_bytes(cp_pubkey_bytes)
        elif length == 2592:
            pubkey = mldsa.MLDSA87PublicKey.from_public_bytes(cp_pubkey_bytes)
        else:
            raise ValueError(f"unsupported length {length}")

        sig_payload = f"{root_hash}_{start_ev}_{end_ev}_{count}".encode()
        pubkey.verify(sig_bytes, sig_payload)
    except InvalidSignature:
        verifier.errors.append(f"checkpoint_signature_invalid:{index}")
        return False
    except Exception as e:
        verifier.errors.append(f"checkpoint_verification_error:{index}:{e}")
        return False

    start_idx = None
    end_idx = None
    for i, ev in enumerate(verifier.events):
        if ev.get("event_id") == start_ev:
            start_idx = i
        if ev.get("event_id") == end_ev:
            end_idx = i

    if start_idx is None or end_idx is None or start_idx > end_idx:
        verifier.errors.append(f"checkpoint_events_not_found:{index}:{start_ev}_to_{end_ev}")
        return False

    slice_events = verifier.events[start_idx : end_idx + 1]
    if len(slice_events) != count:
        verifier.errors.append(
            f"checkpoint_event_count_mismatch:{index}:{len(slice_events)}_vs_{count}"
        )
        return False

    slice_hashes = [_event_hash(ev) for ev in slice_events]
    calculated_root = _merkle_root_v1(slice_hashes)
    if calculated_root != root_hash:
        verifier.errors.append(
            f"checkpoint_merkle_root_mismatch:{index}:{calculated_root}_vs_{root_hash}"
        )
        return False

    return True
