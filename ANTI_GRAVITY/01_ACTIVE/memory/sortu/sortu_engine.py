# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import re
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
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sortu_ledger import SkillLedger, TransitionEvent
from sortu_models import AbortReason, ForgeAbortError, ForgeInvocation, SkillRecord, SortuState
from sortu_overlap import OverlapDetector
from verify_sortu import VerificationError, verify_tripartite


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class SortuEngine:
    def __init__(self, db_conn: sqlite3.Connection, skills_dir: str | Path) -> None:
        self.ledger = SkillLedger(db_conn)
        self.skills_dir = Path(skills_dir)
        self._overlap = OverlapDetector(self.skills_dir)

    @staticmethod
    def _intent_to_name(intent: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", intent.lower()).strip("-")
        return slug or "skill"

    def _abort(
        self,
        inv: ForgeInvocation,
        reason: AbortReason,
        detail: str,
        *,
        artifact_hashes: dict[str, str] | None = None,
    ) -> None:
        record = SkillRecord.new(
            skill_name=self._intent_to_name(inv.intent),
            version="1.0.0",
            artifact_hashes=artifact_hashes or {},
            causal_parent=inv.causal_parent,
            ttl_days=inv.ttl_days,
        )
        self.ledger.register(record)
        self.ledger.transition(record.skill_id, SortuState.ABORTED, abort_reason=reason)
        raise ForgeAbortError(reason, detail)

    def forge(self, inv: ForgeInvocation, *, skill_dir: str | Path | None = None) -> SkillRecord:
        if inv.causal_parent and self.ledger.get(inv.causal_parent) is None:
            self._abort(inv, AbortReason.INVALID_CAUSAL_PARENT, "causal parent not found")

        overlap = self._overlap.decide(
            inv.intent,
            overlap_threshold=inv.overlap_threshold,
            causal_gap_threshold=inv.causal_gap_threshold,
        )
        if overlap.decision == "ABORT_REDUNDANT":
            self._abort(
                inv,
                AbortReason.REDUNDANT_COMPUTATION,
                f"overlap={overlap.overlap_score:.2f}",
            )

        artifact_hashes: dict[str, str] = {}
        if skill_dir is not None:
            try:
                artifact_hashes = verify_tripartite(Path(skill_dir))["artifact_hashes"]
            except VerificationError as exc:
                self._abort(
                    inv,
                    AbortReason.CONTRACT_VERIFICATION_FAILED,
                    str(exc),
                )

        record = SkillRecord.new(
            skill_name=self._intent_to_name(inv.intent),
            version="1.0.0",
            artifact_hashes=artifact_hashes,
            causal_parent=inv.causal_parent,
            ttl_days=inv.ttl_days,
        )
        self.ledger.register(record)
        for state in [
            SortuState.AUDITED,
            SortuState.FORGED,
            SortuState.VERIFIED,
            SortuState.LINKED,
            SortuState.LKRGSERED,
            SortuState.ACTIVE,
        ]:
            self.ledger.transition(record.skill_id, state)
        return self.ledger.get(record.skill_id)  # type: ignore[return-value]

    def quarantine_sweep(self, *, now: datetime | None = None) -> list[TransitionEvent]:
        ref = now or _now_utc()
        events: list[TransitionEvent] = []
        for record in self.ledger.list_by_state(SortuState.ACTIVE):
            if record.ttl_expiration <= ref:
                events.append(self.ledger.transition(record.skill_id, SortuState.QUARANTINED))
        return events

    def tombstone_sweep(
        self,
        *,
        grace_days: int = 7,
        now: datetime | None = None,
    ) -> list[TransitionEvent]:
        ref = now or _now_utc()
        cutoff = ref - timedelta(days=grace_days)
        events: list[TransitionEvent] = []
        for record in self.ledger.list_by_state(SortuState.QUARANTINED):
            if record.ttl_expiration <= cutoff:
                events.append(self.ledger.transition(record.skill_id, SortuState.TOMBSTONED))
        return events

    def purge_sweep(
        self,
        *,
        purge_after_days: int = 30,
        now: datetime | None = None,
    ) -> list[TransitionEvent]:
        ref = now or _now_utc()
        cutoff = ref - timedelta(days=purge_after_days)
        events: list[TransitionEvent] = []
        for record in self.ledger.list_by_state(SortuState.TOMBSTONED):
            if record.ttl_expiration <= cutoff:
                events.append(self.ledger.transition(record.skill_id, SortuState.PURGED))
        return events
