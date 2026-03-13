"""CORTEX v7+ — Procedural Memory & Skill Buffer.

Basal Ganglia analogue: caches recently executed skills, tracking
execution outcomes (striatal valuation) and latencies. Shifts
skill selection from pure semantic matching to reinforcement-based
historical reliability.
"""

from __future__ import annotations

import math
import sqlite3
import time
from dataclasses import dataclass, field
from typing import ClassVar, Final

# ─── Constants ──────────────────────────────────────────────────────────────

# EMA alpha for success rate updates — higher = reacts faster to recent outcomes
_ALPHA_SUCCESS: Final[float] = 0.3

# EMA alpha for latency updates — lower = more stable average
_ALPHA_LATENCY: Final[float] = 0.2

# Temporal decay half-life: striatal value halves every N seconds of disuse
# Set to 30 days (2.592e6 seconds) — matches biological dopaminergic pruning timescale
_DECAY_HALFLIFE_SECONDS: Final[float] = 30 * 24 * 3600.0


# ─── Models ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ProceduralEngram:
    """Frozen representation of a skill's reinforcement history."""

    skill_name: str
    invocations: int = 0
    success_rate: float = 1.0
    avg_latency_ms: float = 0.0
    last_invoked: float = field(default_factory=time.time)
    permanent: bool = False
    """If True, skip temporal decay — skill is always fully valued."""

    def __post_init__(self) -> None:
        """Enforce architectural constraints (Ω₄).
        Omega-tier skills are permanent by definition — the system prohibits
        non-permanent omegas at the logical layer.
        """
        if "omega" in self.skill_name.lower() and not self.permanent:
            object.__setattr__(self, "permanent", True)

    @property
    def striatal_value(self) -> float:
        """Valuation score — combines success rate, usage frequency, and recency decay.

        Analogue to Striatal valuation in the Basal Ganglia:
          - Success rate is the primary driver.
          - Frequency (log-scaled) provides a small bonus for well-practiced skills.
          - Temporal decay penalizes skills not used recently (dopaminergic pruning).
            A skill unused for 30 days recovers 50% of its potential score at most.
          - Omega-tier skills bypass decay by design.
        """
        # ... rest of the logic ...
        frequency_bonus = math.log10(self.invocations + 1) * 0.1
        raw = min(1.0, self.success_rate + frequency_bonus)

        if self.permanent:
            return raw

        # Exponential decay: value *= 2^(-elapsed / halflife)
        elapsed = max(0.0, time.time() - self.last_invoked)
        decay = math.pow(2.0, -elapsed / _DECAY_HALFLIFE_SECONDS)
        return raw * decay


# ─── Memory ─────────────────────────────────────────────────────────────────


class ProceduralMemory:
    """Skill Buffer with reinforcement tracking.

    Provides O(1) access to execution history for any skill slug,
    updating EMA success rates and latencies on each invocation.
    Now backed by SQLite.
    """

    BASELINE_LATENCY_MS: ClassVar[float] = 100.0

    def __init__(self, db_path: str | None = None) -> None:
        self._buffer: dict[str, ProceduralEngram] = {}
        self._db_path = db_path
        self._load_from_db()

    def _get_connection(self):
        """Get a connection to the SQLite database if active."""
        if not self._db_path:
            return None
        import sqlite3

        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _load_from_db(self) -> None:
        """Load existing engrams from the database into the in-memory buffer."""
        conn = self._get_connection()
        if not conn:
            return

        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT skill_name, invocations, success_rate, avg_latency_ms, "
                "last_invoked, permanent FROM procedural_engrams"
            )
            rows = cur.fetchall()
            for row in rows:
                self._buffer[row["skill_name"]] = ProceduralEngram(
                    skill_name=row["skill_name"],
                    invocations=row["invocations"],
                    success_rate=row["success_rate"],
                    avg_latency_ms=row["avg_latency_ms"],
                    last_invoked=row["last_invoked"],
                    permanent=bool(row["permanent"]),
                )
        except sqlite3.OperationalError as e:
            if "no such table" not in str(e):
                import logging
                logging.getLogger("cortex.memory.procedural").error(
                    "DB Operational error on load: %s", e
                )
                from cortex.swarm.error_ghost_pipeline import ErrorGhostPipeline
                ErrorGhostPipeline().capture_sync(
                    e, source="procedural:load", project="CORTEX_SYSTEM"
                )
        except Exception as e:  # noqa: BLE001
            import logging
            logging.getLogger("cortex.memory.procedural").error(
                "Unexpected procedural load error: %s", e
            )
            from cortex.swarm.error_ghost_pipeline import ErrorGhostPipeline
            ErrorGhostPipeline().capture_sync(
                e, source="procedural:load", project="CORTEX_SYSTEM"
            )
        finally:
            conn.close()

    def _save_to_db(self, engram: ProceduralEngram) -> None:
        """Persist a single engram to the database."""
        conn = self._get_connection()
        if not conn:
            return

        try:
            cur = conn.cursor()
            import sqlite3

            cur.execute(
                """
                INSERT INTO procedural_engrams 
                (skill_name, invocations, success_rate, avg_latency_ms, last_invoked, permanent)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(skill_name) DO UPDATE SET
                    invocations=excluded.invocations,
                    success_rate=excluded.success_rate,
                    avg_latency_ms=excluded.avg_latency_ms,
                    last_invoked=excluded.last_invoked,
                    permanent=excluded.permanent
                """,
                (
                    engram.skill_name,
                    engram.invocations,
                    engram.success_rate,
                    engram.avg_latency_ms,
                    engram.last_invoked,
                    int(engram.permanent),
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError as e:
            # Let the 1->0 immutable trigger fail silently during standard execution
            # Or raise if strict enforcement is preferred. We just catch to avoid crashing.
            if "Immunitas-Omega" not in str(e):
                raise
        finally:
            conn.close()

    def get_engram(self, skill_name: str) -> ProceduralEngram | None:
        """Fetch the engram for a specific skill. O(1)."""
        return self._buffer.get(skill_name)

    def record_execution(
        self,
        skill_name: str,
        success: bool,
        latency_ms: float,
        permanent: bool = False,
    ) -> None:
        """Record the outcome of a skill execution.

        Updates EMA success rate and latency.
        Time complexity: O(1) in-memory, plus asynchronous/synchronous write to DB.
        """
        existing = self._buffer.get(skill_name)
        now = time.time()

        if not existing:
            new_engram = ProceduralEngram(
                skill_name=skill_name,
                invocations=1,
                success_rate=1.0 if success else 0.0,
                avg_latency_ms=latency_ms,
                last_invoked=now,
                permanent=permanent,
            )
            self._buffer[skill_name] = new_engram
            self._save_to_db(new_engram)
            return

        outcome = 1.0 if success else 0.0
        new_success_rate = _ALPHA_SUCCESS * outcome + (1.0 - _ALPHA_SUCCESS) * existing.success_rate
        new_avg_latency = (
            _ALPHA_LATENCY * latency_ms + (1.0 - _ALPHA_LATENCY) * existing.avg_latency_ms
        )

        # Enforce that a skill mark as permanent once cannot be un-marked locally either
        is_permanent = permanent or existing.permanent

        new_engram = ProceduralEngram(
            skill_name=skill_name,
            invocations=existing.invocations + 1,
            success_rate=new_success_rate,
            avg_latency_ms=new_avg_latency,
            last_invoked=now,
            permanent=is_permanent,
        )

        self._buffer[skill_name] = new_engram
        self._save_to_db(new_engram)

    def top_skills(self, limit: int = 5) -> list[ProceduralEngram]:
        """Return the highest-value skills by striatal valuation."""
        engrams = sorted(self._buffer.values(), key=lambda x: x.striatal_value, reverse=True)
        return engrams[:limit]
