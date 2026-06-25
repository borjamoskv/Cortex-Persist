# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import hashlib
import sqlite3

# --- C5-REAL BFT PATCH (R10) ---
import sqlite3 as _sqlite3_bft_orig
_orig_sqlite_connect = _sqlite3_bft_orig.connect
def _bft_sqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    conn = _orig_sqlite_connect(*args, **kwargs)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn
_sqlite3_bft_orig.connect = _bft_sqlite_connect
# -------------------------------
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from legacy_research.ledger.models import LedgerEvent, LedgerOriginSignature
from legacy_research.ledger.public_verifier_utils import _canonical_public_json


class ReplayAdmissionError(ValueError):
    """Raised when online replay or freshness admission rejects an event."""

    preserve_ledger_error = True


ReplayAdmissionStatus = Literal["accepted", "idempotent"]


@dataclass(frozen=True)
class ReplayAdmissionResult:
    status: ReplayAdmissionStatus
    event_id: str


@dataclass(frozen=True)
class ReplayAdmissionPolicy:
    max_age_seconds: int = 300
    future_skew_seconds: int = 30
    enforce_online_freshness: bool = True
    idempotent_retries: bool = True
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)

    def validate_event(self, event: LedgerEvent) -> None:
        origin = _require_origin(event)
        if not self.enforce_online_freshness:
            return
        now = _normalize_aware(self.now(), "online_freshness_now_invalid")
        issued_at = _parse_utc(origin.issued_at)
        if issued_at > now + timedelta(seconds=self.future_skew_seconds):
            raise ReplayAdmissionError("online_freshness_future_event")
        if issued_at < now - timedelta(seconds=self.max_age_seconds):
            raise ReplayAdmissionError("online_freshness_stale_event")

    def admit_event(
        self,
        conn: sqlite3.Connection,
        event: LedgerEvent,
    ) -> ReplayAdmissionResult:
        origin = _require_origin(event)
        tenant_id = _require_tenant(event, origin)
        request_hash = replay_request_hash(event)
        try:
            conn.execute(
                """
                INSERT INTO ledger_replay_admissions (
                    tenant_id,
                    event_id,
                    nonce,
                    request_hash,
                    payload_hash,
                    ledger_event_id,
                    actor_key_id,
                    action,
                    issued_at,
                    accepted_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    event.event_id,
                    origin.nonce,
                    request_hash,
                    origin.payload_hash,
                    event.event_id,
                    origin.actor_key_id,
                    event.action,
                    origin.issued_at,
                    _format_utc(_normalize_aware(self.now(), "online_freshness_now_invalid")),
                ),
            )
        except sqlite3.IntegrityError:
            return self._classify_existing(conn, event, origin, tenant_id, request_hash)
        return ReplayAdmissionResult(status="accepted", event_id=event.event_id)

    def _classify_existing(
        self,
        conn: sqlite3.Connection,
        event: LedgerEvent,
        origin: LedgerOriginSignature,
        tenant_id: str,
        request_hash: str,
    ) -> ReplayAdmissionResult:
        rows = conn.execute(
            """
            SELECT event_id, nonce, request_hash, ledger_event_id
            FROM ledger_replay_admissions
            WHERE tenant_id = ? AND (event_id = ? OR nonce = ?)
            ORDER BY id ASC
            """,
            (tenant_id, event.event_id, origin.nonce),
        ).fetchall()
        exact = [
            row
            for row in rows
            if row["event_id"] == event.event_id
            and row["nonce"] == origin.nonce
            and row["request_hash"] == request_hash
        ]
        if exact and self.idempotent_retries:
            return ReplayAdmissionResult(
                status="idempotent",
                event_id=str(exact[0]["ledger_event_id"]),
            )

        event_matches = [row for row in rows if row["event_id"] == event.event_id]
        nonce_matches = [row for row in rows if row["nonce"] == origin.nonce]
        if event_matches and nonce_matches:
            raise ReplayAdmissionError(f"replay_retry_mutated:{tenant_id}:{event.event_id}")
        if event_matches:
            raise ReplayAdmissionError(f"replay_event_id_duplicate:{tenant_id}:{event.event_id}")
        if nonce_matches:
            raise ReplayAdmissionError(f"replay_nonce_duplicate:{tenant_id}:{origin.nonce}")
        raise ReplayAdmissionError(f"replay_admission_conflict:{tenant_id}:{event.event_id}")


def replay_request_hash(event: LedgerEvent) -> str:
    payload = event.to_payload()
    payload.pop("hash", None)
    payload.pop("prev_hash", None)
    return hashlib.sha256(_canonical_public_json(payload).encode("utf-8")).hexdigest()


def validate_batch_import_manifest(export_dir: str | Path) -> dict[str, Any]:
    root = Path(export_dir)
    if not (root / "manifest.json").exists():
        raise ReplayAdmissionError("batch_import_manifest_missing")

    from legacy_research.ledger.public_verifier import verify_export

    report = verify_export(root)
    if report.get("result") != "VALID_FULL_STRICT":
        raise ReplayAdmissionError(f"batch_import_not_full_strict:{report.get('result')}")
    return report


def _require_origin(event: LedgerEvent) -> LedgerOriginSignature:
    if event.origin is None:
        raise ReplayAdmissionError("replay_origin_missing")
    if not event.origin.nonce:
        raise ReplayAdmissionError("replay_nonce_missing")
    return event.origin


def _require_tenant(event: LedgerEvent, origin: LedgerOriginSignature) -> str:
    tenant_id = event.metadata.get("tenant_id")
    if not isinstance(tenant_id, str) or not tenant_id:
        raise ReplayAdmissionError("replay_tenant_missing")
    if tenant_id != origin.tenant_id:
        raise ReplayAdmissionError("replay_tenant_mismatch")
    return tenant_id


def _parse_utc(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ReplayAdmissionError("online_freshness_timestamp_invalid") from exc
    if parsed.tzinfo is None:
        raise ReplayAdmissionError("online_freshness_timestamp_missing_timezone")
    return parsed


def _normalize_aware(value: datetime, error_code: str) -> datetime:
    if value.tzinfo is None:
        raise ReplayAdmissionError(error_code)
    return value.astimezone(timezone.utc)


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
