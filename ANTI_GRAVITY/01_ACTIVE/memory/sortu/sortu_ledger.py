# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import json
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
from dataclasses import dataclass
from datetime import datetime, timezone

from sortu_models import AbortReason, SkillRecord, SortuState, YieldEvent, validate_transition


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class TransitionEvent:
    skill_id: str
    from_state: SortuState
    to_state: SortuState
    changed_at: datetime


class SkillLedger:
    def __init__(self, db_conn: sqlite3.Connection) -> None:
        self.conn = db_conn
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sortu_skills (
                skill_id TEXT PRIMARY KEY,
                skill_name TEXT NOT NULL,
                version TEXT NOT NULL,
                artifact_hashes TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL,
                ttl_expiration TEXT NOT NULL,
                causal_parent TEXT,
                purge_status TEXT NOT NULL,
                abort_reason TEXT,
                verification_status TEXT
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sortu_yield_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_id TEXT NOT NULL,
                hours_saved REAL NOT NULL,
                days_since INTEGER NOT NULL,
                verified INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sortu_transitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_id TEXT NOT NULL,
                from_state TEXT NOT NULL,
                to_state TEXT NOT NULL,
                changed_at TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def register(self, record: SkillRecord) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO sortu_skills (
                skill_id, skill_name, version, artifact_hashes, state, created_at,
                ttl_expiration, causal_parent, purge_status, abort_reason, verification_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.skill_id,
                record.skill_name,
                record.version,
                json.dumps(record.artifact_hashes, sort_keys=True),
                record.state.value,
                record.created_at.isoformat(),
                record.ttl_expiration.isoformat(),
                record.causal_parent,
                record.purge_status,
                record.abort_reason.value if record.abort_reason else None,
                record.verification_status,
            ),
        )
        self.conn.commit()

    def get(self, skill_id: str) -> SkillRecord | None:
        row = self.conn.execute(
            "SELECT * FROM sortu_skills WHERE skill_id = ?",
            (skill_id,),
        ).fetchone()
        if row is None:
            return None
        return self._hydrate_record(row)

    def _hydrate_record(self, row: sqlite3.Row) -> SkillRecord:
        yield_rows = self.conn.execute(
            """
            SELECT hours_saved, days_since, verified
            FROM sortu_yield_events
            WHERE skill_id = ?
            ORDER BY id
            """,
            (row["skill_id"],),
        ).fetchall()
        return SkillRecord(
            skill_id=row["skill_id"],
            skill_name=row["skill_name"],
            version=row["version"],
            artifact_hashes=json.loads(row["artifact_hashes"]),
            state=SortuState(row["state"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            ttl_expiration=datetime.fromisoformat(row["ttl_expiration"]),
            causal_parent=row["causal_parent"],
            purge_status=row["purge_status"],
            abort_reason=AbortReason(row["abort_reason"]) if row["abort_reason"] else None,
            verification_status=row["verification_status"],
            yield_events=[
                YieldEvent(
                    hours_saved=float(y["hours_saved"]),
                    days_since=int(y["days_since"]),
                    verified=bool(y["verified"]),
                )
                for y in yield_rows
            ],
        )

    def transition(
        self,
        skill_id: str,
        to_state: SortuState,
        *,
        abort_reason: AbortReason | None = None,
    ) -> TransitionEvent:
        record = self.get(skill_id)
        if record is None:
            raise ValueError(f"Skill {skill_id} not found")
        if not validate_transition(record.state, to_state):
            raise ValueError(f"Illegal transition: {record.state.value} -> {to_state.value}")

        changed_at = _now_utc()
        verification_status = record.verification_status
        purge_status = record.purge_status
        if to_state == SortuState.VERIFIED:
            verification_status = "PASS"
        if to_state == SortuState.PURGED:
            purge_status = "PURGED"

        self.conn.execute(
            """
            UPDATE sortu_skills
            SET state = ?, abort_reason = ?, verification_status = ?, purge_status = ?
            WHERE skill_id = ?
            """,
            (
                to_state.value,
                abort_reason.value
                if abort_reason
                else record.abort_reason.value
                if record.abort_reason
                else None,
                verification_status,
                purge_status,
                skill_id,
            ),
        )
        self.conn.execute(
            """
            INSERT INTO sortu_transitions (skill_id, from_state, to_state, changed_at)
            VALUES (?, ?, ?, ?)
            """,
            (skill_id, record.state.value, to_state.value, changed_at.isoformat()),
        )
        self.conn.commit()
        return TransitionEvent(
            skill_id=skill_id,
            from_state=record.state,
            to_state=to_state,
            changed_at=changed_at,
        )

    def record_yield_event(self, skill_id: str, event: YieldEvent) -> None:
        self.conn.execute(
            """
            INSERT INTO sortu_yield_events (skill_id, hours_saved, days_since, verified)
            VALUES (?, ?, ?, ?)
            """,
            (skill_id, event.hours_saved, event.days_since, int(event.verified)),
        )
        self.conn.commit()

    def list_by_state(self, state: SortuState) -> list[SkillRecord]:
        rows = self.conn.execute(
            "SELECT * FROM sortu_skills WHERE state = ? ORDER BY created_at, skill_name",
            (state.value,),
        ).fetchall()
        return [self._hydrate_record(row) for row in rows]

    def list_quarantine_candidates(self, *, now: datetime | None = None) -> list[SkillRecord]:
        ref = now or _now_utc()
        return [
            record
            for record in self.list_by_state(SortuState.ACTIVE)
            if record.ttl_expiration <= ref
        ]
