# [C5-REAL] Exergy-Maximized
"""
Billing Schema Integrity Gateway.

Immutable ledger proxy for all Stripe billing webhooks.
Ensures zero state mutations occur imperatively inside HTTP routes.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from cortex.config import DB_PATH
from cortex.database.core import connect_async_ctx

logger = logging.getLogger(__name__)


class BillingIntegrityGateway:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or DB_PATH

    async def initialize(self) -> None:
        """Ensure ledger_events schema is present."""
        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "schema", "events_log.sql"
        )
        if os.path.exists(schema_path):
            with open(schema_path) as f:
                schema_sql = f.read()
            async with connect_async_ctx(self.db_path) as conn:
                await conn.executescript(schema_sql)
                await conn.commit()

    async def append_billing_event(
        self, event_type: str, payload: dict[str, Any], actor: str = "stripe"
    ) -> str:
        """Append an event to the ledger with 'pending' status."""
        event_id = f"evt_{uuid.uuid4().hex}"
        payload_json = json.dumps(payload)
        ts = datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()

        async with connect_async_ctx(self.db_path) as conn:
            await conn.execute(
                """
                INSERT INTO ledger_events (event_id, ts, tool, actor, action, payload_json, semantic_status)
                VALUES (?, ?, ?, ?, ?, ?, 'pending')
                """,
                (event_id, ts, "billing_gateway", actor, event_type, payload_json),
            )
            await conn.commit()

        # Fire and forget processing
        asyncio.create_task(self.process_pending_events())
        return event_id

    async def process_pending_events(self) -> None:
        """Process 'pending' billing events asynchronously."""
        async with connect_async_ctx(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                """
                SELECT * FROM ledger_events 
                WHERE semantic_status = 'pending' AND tool = 'billing_gateway' 
                ORDER BY ts ASC
                """
            )
            rows = await cursor.fetchall()

            for row in rows:
                event_id = row["event_id"]
                action = row["action"]
                payload = json.loads(row["payload_json"])

                try:
                    await self._handle_event(action, payload)
                    await conn.execute(
                        "UPDATE ledger_events SET semantic_status = 'applied' WHERE event_id = ?",
                        (event_id,),
                    )
                except Exception as e:
                    logger.exception("Failed to process billing event %s", event_id)
                    await conn.execute(
                        "UPDATE ledger_events SET semantic_status = 'error', semantic_error = ? WHERE event_id = ?",
                        (str(e), event_id),
                    )
            await conn.commit()

    async def _handle_event(self, action: str, payload: dict[str, Any]) -> None:
        """Route the specific action to the AuthManager."""
        # We decouple imperative logic from stripe.py
        import cortex.api.state as api_state

        if action == "checkout.session.completed":
            session = payload["data"]["object"]
            customer_email = session.get("customer_email") or session.get(
                "customer_details", {}
            ).get("email", "unknown")
            plan = session.get("metadata", {}).get("plan", "pro")

            if api_state.auth_manager:
                from cortex.routes.stripe import PLAN_CONFIG

                plan_cfg = PLAN_CONFIG.get(plan, PLAN_CONFIG["pro"])
                await api_state.auth_manager.create_key(
                    name=f"stripe-{customer_email}",
                    tenant_id=customer_email,
                    permissions=plan_cfg["permissions"],
                    rate_limit=plan_cfg["rate_limit"],
                )
                logger.info(
                    "Ledger applied: provisioned key for %s (Plan: %s)", customer_email, plan
                )

        elif action == "customer.subscription.deleted":
            subscription = payload["data"]["object"]
            customer_id = subscription.get("customer", "")

            from cortex.routes.stripe import _get_stripe

            stripe_obj = _get_stripe()
            customer = stripe_obj.Customer.retrieve(customer_id)
            email = customer.get("email", "")

            if email and api_state.auth_manager:
                keys = await api_state.auth_manager.list_keys(tenant_id=email)
                for key in keys:
                    if key.name.startswith("stripe-"):
                        await api_state.auth_manager.revoke_key(key.id)
                        logger.info("Ledger applied: revoked key %s for %s", key.name, email)


# Global singleton
_billing_gateway = BillingIntegrityGateway()


def get_billing_gateway() -> BillingIntegrityGateway:
    return _billing_gateway
