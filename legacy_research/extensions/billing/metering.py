# [C5-REAL] Exergy-Maximized
"""CORTEX Billing Core - Causal Metering & Economic Entropy Engine.

Tracks compute units (SSU), calculates execution costs based on failure type,
implements SQLite database persistence, and computes net exergy.
"""

from __future__ import annotations

import json
import logging
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

from legacy_research.extensions.billing.gateway import StripeBillingGateway
from legacy_research.extensions.billing.models import BillingEvent, FailureType

logger = logging.getLogger(__name__)

_BILLING_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS billing_events (
    event_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    ssu_units REAL NOT NULL,
    cost_usd REAL NOT NULL,
    causal_link TEXT NOT NULL,
    reproducibility_score REAL NOT NULL,
    exploitability_index REAL NOT NULL,
    failure_type TEXT,
    revenue_quarantined INTEGER NOT NULL DEFAULT 0,
    timestamp INTEGER NOT NULL,
    meta TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_billing_agent_ts
    ON billing_events(agent_id, timestamp);
"""


class CausalMetering:
    """Causal Metering Engine evaluating computational cost and exergy dynamics."""

    def __init__(self, db_path: str | None = None, gateway: StripeBillingGateway | None = None):
        if db_path is None:
            from legacy_research.core.config import DB_PATH
            db_path = DB_PATH

        self._db_path = db_path
        self._gateway = gateway or StripeBillingGateway()
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path) # type: ignore
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript(_BILLING_SCHEMA_SQL)
        conn.commit()

    def calculate_cost(
        self,
        duration: float,
        tokens_used: int,
        search_depth: int = 1,
        failure_type: FailureType | None = None,
    ) -> tuple[float, float]:
        """Calculate Standard Swarm Units (SSU) and total cost in USD.

        SSU Formula:
            SSU = (duration * 1.5) + (tokens_used * 0.0001) + (search_depth * 2.0)

        Failure Rate Multipliers:
            - None: 1.0 (Successful run)
            - F1 (Stochastic): 0.5 (Reduction for baseline noise)
            - F2 (Induced/Adversarial): 2.0 (Double penalty rate for exploit/pen testing)
            - F3 (Synthetic): 1.0 (Full monetizable rate)

        Returns:
            Tuple of (ssu_units, cost_usd).
        """
        ssu = (duration * 1.5) + (tokens_used * 0.0001) + (search_depth * 2.0)
        base_cost = ssu * 0.01  # $0.01 per SSU baseline rate

        multiplier = 1.0
        if failure_type == FailureType.F1:
            multiplier = 0.5
        elif failure_type == FailureType.F2:
            multiplier = 2.0
        elif failure_type == FailureType.F3:
            multiplier = 1.0

        cost = base_cost * multiplier
        return round(ssu, 4), round(cost, 6)

    def evaluate_exergy(
        self,
        monthly_income: float,
        entropy: float,
        novelty: float,
        lmbda: float = 0.5,
        mu: float = 0.2,
    ) -> float:
        """Applies mathematical anti-gravity term to calculate net exergy.

        Formula:
            E_net = E_income - λ * entropy + μ * novelty

        Returns:
            Computed net exergy.
        """
        e_net = monthly_income - (lmbda * entropy) + (mu * novelty)
        return round(e_net, 4)

    def record_billing_event(self, event: BillingEvent) -> None:
        """Record billing event in SQLite and run gateway quarantine check."""
        if event.failure_type == FailureType.F2:
            self._gateway.quarantine_revenue(event)

        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO billing_events (event_id, agent_id, ssu_units, cost_usd, "
            "causal_link, reproducibility_score, exploitability_index, failure_type, "
            "revenue_quarantined, timestamp, meta) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event.event_id,
                event.agent_id,
                event.ssu_units,
                event.cost_usd,
                event.causal_link,
                event.reproducibility_score,
                event.exploitability_index,
                event.failure_type.value if event.failure_type else None,
                1 if event.revenue_quarantined else 0,
                event.timestamp,
                json.dumps(event.meta),
            ),
        )
        conn.commit()
        logger.info(
            "[METERING] Recorded billing event %s for agent %s (SSU=%.2f, Cost=$%.4f)",
            event.event_id,
            event.agent_id,
            event.ssu_units,
            event.cost_usd,
        )

    def get_billing_events(self, agent_id: str | None = None) -> list[BillingEvent]:
        """Retrieve billing events from database."""
        conn = self._get_conn()
        if agent_id:
            rows = conn.execute(
                "SELECT * FROM billing_events WHERE agent_id = ? ORDER BY timestamp DESC",
                (agent_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM billing_events ORDER BY timestamp DESC"
            ).fetchall()

        events = []
        for r in rows:
            ft = r["failure_type"]
            failure_type = FailureType(ft) if ft else None
            meta = {}
            if r["meta"]:
                try:
                    meta = json.loads(r["meta"])
                except Exception:
                    pass

            events.append(
                BillingEvent(
                    agent_id=r["agent_id"],
                    ssu_units=r["ssu_units"],
                    cost_usd=r["cost_usd"],
                    causal_link=r["causal_link"],
                    reproducibility_score=r["reproducibility_score"],
                    exploitability_index=r["exploitability_index"],
                    failure_type=failure_type,
                    revenue_quarantined=bool(r["revenue_quarantined"]),
                    event_id=r["event_id"],
                    timestamp=r["timestamp"],
                    meta=meta,
                )
            )
        return events

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> CausalMetering:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
