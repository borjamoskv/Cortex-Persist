from __future__ import annotations

import base64
import binascii
import dataclasses
import secrets
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from cortex.ledger.models import LedgerEvent, LedgerOriginSignature
from cortex.utils.canonical import canonical_json


class OriginSignatureError(ValueError):
    """Raised when a ledger event fails origin-authenticity validation."""


@dataclass(frozen=True)
class OriginKeyRecord:
    key_id: str
    actor_id: str
    public_key: Ed25519PublicKey
    permissions: frozenset[str]
    actor_type: str = "agent"
    status: str = "active"
    environment: str = "test"
    valid_from: str | None = None
    valid_until: str | None = None
    hardware_backed: bool = False

    @staticmethod
    def from_public_key(
        *,
        key_id: str,
        actor_id: str,
        public_key: Ed25519PublicKey,
        permissions: Sequence[str],
        actor_type: str = "agent",
        status: str = "active",
        environment: str = "test",
        valid_from: str | None = None,
        valid_until: str | None = None,
        hardware_backed: bool = False,
    ) -> OriginKeyRecord:
        return OriginKeyRecord(
            key_id=key_id,
            actor_id=actor_id,
            public_key=public_key,
            permissions=frozenset(permissions),
            actor_type=actor_type,
            status=status,
            environment=environment,
            valid_from=valid_from,
            valid_until=valid_until,
            hardware_backed=hardware_backed,
        )

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "algorithm": "ed25519",
            "environment": self.environment,
            "hardware_backed": self.hardware_backed,
            "key_id": self.key_id,
            "permissions": sorted(self.permissions),
            "public_key": _public_key_b64url(self.public_key),
            "status": self.status,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
        }


class OriginKeyRegistry:
    def __init__(self, records: Sequence[OriginKeyRecord] = ()) -> None:
        self._records: dict[str, OriginKeyRecord] = {}
        for record in records:
            self.add(record)

    def add(self, record: OriginKeyRecord) -> None:
        if record.key_id in self._records:
            raise ValueError(f"duplicate origin key id: {record.key_id}")
        self._records[record.key_id] = record

    def get(self, key_id: str) -> OriginKeyRecord | None:
        return self._records.get(key_id)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "keys": [
                record.to_public_dict()
                for record in sorted(self._records.values(), key=lambda item: item.key_id)
            ],
            "schema_version": "cortex-origin-key-registry-v1",
        }


@dataclass(frozen=True)
class OriginSignaturePolicy:
    registry: OriginKeyRegistry
    strict: bool = True

    @staticmethod
    def strict_mode(registry: OriginKeyRegistry) -> OriginSignaturePolicy:
        return OriginSignaturePolicy(registry=registry, strict=True)

    def validate_event(self, event: LedgerEvent) -> None:
        if not self.strict:
            return
        verify_event_origin(event, self.registry)


def sign_event_origin(
    event: LedgerEvent,
    *,
    key_id: str,
    private_key: Ed25519PrivateKey,
    signed_at: str | None = None,
    nonce: str | None = None,
) -> LedgerEvent:
    """Attach an Ed25519 origin envelope to an event before ledger persistence."""
    unsigned_origin = LedgerOriginSignature(
        actor_id=event.actor,
        key_id=key_id,
        signature_alg="ed25519",
        signed_at=signed_at or _utc_now(),
        nonce=nonce or secrets.token_urlsafe(24),
        signature=None,
    )
    unsigned_event = dataclasses.replace(event, origin=unsigned_origin)
    signature = _b64url_encode(private_key.sign(origin_signature_scope(unsigned_event)))
    signed_origin = dataclasses.replace(unsigned_origin, signature=signature)
    return dataclasses.replace(unsigned_event, origin=signed_origin)


def verify_event_origin(event: LedgerEvent, registry: OriginKeyRegistry) -> None:
    origin = event.origin
    if origin is None or not origin.signature:
        raise OriginSignatureError("origin_signature_missing")
    if origin.signature_alg != "ed25519":
        raise OriginSignatureError(f"origin_signature_alg_unsupported:{origin.signature_alg}")
    if origin.actor_id != event.actor:
        raise OriginSignatureError("origin_actor_mismatch")

    key = registry.get(origin.key_id)
    if key is None:
        raise OriginSignatureError(f"origin_key_missing:{origin.key_id}")
    if key.status != "active":
        raise OriginSignatureError(f"origin_key_not_active:{origin.key_id}")
    if key.actor_id != origin.actor_id:
        raise OriginSignatureError("origin_key_actor_mismatch")
    if event.action not in key.permissions:
        raise OriginSignatureError(f"origin_key_permission_denied:{event.action}")
    _validate_key_time(key, origin.signed_at)

    try:
        key.public_key.verify(_b64url_decode(origin.signature), origin_signature_scope(event))
    except (InvalidSignature, ValueError) as exc:
        raise OriginSignatureError("origin_signature_invalid") from exc


def origin_signature_scope(event: LedgerEvent) -> bytes:
    payload = event.to_payload()
    payload.pop("hash", None)
    payload.pop("prev_hash", None)
    origin = payload.get("origin")
    if not isinstance(origin, dict):
        raise OriginSignatureError("origin_signature_missing")
    signature_scope = dict(origin)
    signature_scope.pop("signature", None)
    payload["origin"] = signature_scope
    return canonical_json(payload).encode("utf-8")


def _validate_key_time(key: OriginKeyRecord, signed_at: str) -> None:
    signed = _parse_utc(signed_at)
    if key.valid_from is not None and signed < _parse_utc(key.valid_from):
        raise OriginSignatureError(f"origin_key_not_yet_valid:{key.key_id}")
    if key.valid_until is not None and signed > _parse_utc(key.valid_until):
        raise OriginSignatureError(f"origin_key_expired:{key.key_id}")


def _parse_utc(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise OriginSignatureError("origin_timestamp_invalid") from exc
    if parsed.tzinfo is None:
        raise OriginSignatureError("origin_timestamp_missing_timezone")
    return parsed


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    if not value:
        raise ValueError("empty_base64url")
    padding = "=" * (-len(value) % 4)
    try:
        return base64.b64decode((value + padding).encode("ascii"), altchars=b"-_", validate=True)
    except (binascii.Error, UnicodeEncodeError) as exc:
        raise ValueError("invalid_base64url") from exc


def _public_key_b64url(public_key: Ed25519PublicKey) -> str:
    return _b64url_encode(public_key.public_bytes(Encoding.Raw, PublicFormat.Raw))
