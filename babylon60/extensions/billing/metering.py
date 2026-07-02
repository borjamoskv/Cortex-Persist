# [C5-REAL] Exergy-Maximized
"""CORTEX Billing Core - Causal Metering & Economic Entropy Engine.

Tracks compute units (SSU), calculates execution costs based on failure type,
implements SQLite database persistence, and computes net exergy.
"""

from __future__ import annotations

import json
import logging
import sqlite3

from babylon60.extensions.billing.gateway import StripeBillingGateway
from babylon60.extensions.billing.models import BillingEvent, FailureType

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
            from babylon60.core.config import DB_PATH

            db_path = DB_PATH

        self._db_path = db_path
        self._gateway = gateway or StripeBillingGateway()
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)  # type: ignore
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
            rows = conn.execute("SELECT * FROM billing_events ORDER BY timestamp DESC").fetchall()

        events = []
        for r in rows:
            ft = r["failure_type"]
            failure_type = FailureType(ft) if ft else None
            meta = {}
            if r["meta"]:
                try:
                    meta = json.loads(r["meta"])
                except (ValueError, TypeError, OSError, KeyError):
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


import asyncio
from collections import defaultdict
from typing import Any


class AsyncStripeSyncer:
    """Buffer asíncrono para reportar el uso a Stripe en lotes (evita Rate Limits de la API)."""

    _instance: AsyncStripeSyncer | None = None

    def __init__(self):
        self.usage_buffer: dict[tuple[str, str], int] = defaultdict(int)
        self.lock = asyncio.Lock()
        self._sync_task: asyncio.Task | None = None

    @classmethod
    def singleton(cls) -> AsyncStripeSyncer:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def queue_usage(self, api_key: str, tenant_id: str, ssu_cost: int = 1) -> None:
        """Encola el uso O(1) en RAM."""
        if self._sync_task is None:
            self._sync_task = asyncio.create_task(self._sync_loop())

        async with self.lock:
            self.usage_buffer[(api_key, tenant_id)] += ssu_cost

    async def _sync_loop(self) -> None:
        """Loop en background para flushear a Stripe cada 60 segundos."""
        from babylon60.core import config

        try:
            import stripe
        except ImportError:
            stripe = None

        while True:
            await asyncio.sleep(60.0)
            async with self.lock:
                if not self.usage_buffer:
                    continue
                to_sync = dict(self.usage_buffer)
                self.usage_buffer.clear()

            if stripe is None or not getattr(config, "STRIPE_SECRET_KEY", None):
                continue

            stripe.api_key = config.STRIPE_SECRET_KEY

            # Sincronizamos en threads separados
            for (api_key, tenant_id), amount in to_sync.items():
                if amount <= 0:
                    continue
                # Aquí requerimos un acceso a BD para sacar el stripe_subscription_item_id
                # Para aislar, lo hacemos en una tarea separada para no bloquear todo el loop.
                asyncio.create_task(self._report_batch(api_key, tenant_id, amount, stripe))

    async def _report_batch(
        self, api_key: str, tenant_id: str, amount: int, stripe_lib: Any
    ) -> None:
        try:
            import json
            import sqlite3

            from babylon60.core.config import DB_PATH

            stripe_subscription_item_id = None

            def _fetch_sub_id():
                with sqlite3.connect(DB_PATH) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT config FROM tenants WHERE id = ?", (tenant_id,))
                    row = cur.fetchone()
                    if row:
                        cfg = json.loads(row[0])
                        return cfg.get("stripe_subscription_item_id")
                return None

            stripe_subscription_item_id = await asyncio.to_thread(_fetch_sub_id)

            if not stripe_subscription_item_id:
                if not stripe_lib.api_key or stripe_lib.api_key.startswith("sk_test_mock"):
                    stripe_subscription_item_id = f"si_{api_key[-8:]}"
                else:
                    return

            await asyncio.to_thread(
                stripe_lib.SubscriptionItem.create_usage_record,
                stripe_subscription_item_id,
                quantity=amount,
                timestamp="now",
                action="increment",
            )
            logger.info("Stripe bulk usage (%d units) reported for tenant %s", amount, tenant_id)
        except Exception as exc:
            logger.error("Failed to sync bulk usage to Stripe for %s: %s", tenant_id, exc)


def get_stripe_syncer() -> AsyncStripeSyncer:
    return AsyncStripeSyncer.singleton()
