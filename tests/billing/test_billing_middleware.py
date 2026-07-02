# [C5-REAL] Exergy-Maximized Stripe Billing Middleware tests
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts" / "lab"))

import asyncio
import json
import sqlite3
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import Request
from babylon60.api.middleware import CortexBillingMiddleware
from babylon60.auth.models import AuthResult


class FakePool:
    def __init__(self, row_value):
        self.row_value = row_value

    def acquire(self):
        class AsyncCM:
            def __init__(self, row_val):
                self.row_val = row_val
                self.conn = MagicMock()

                class ExecuteCM:
                    def __init__(self, r_val):
                        self.r_val = r_val

                    async def __aenter__(self):
                        cursor = AsyncMock()
                        cursor.fetchone.return_value = (
                            (self.r_val,) if self.r_val is not None else None
                        )
                        return cursor

                    async def __aexit__(self, exc_type, exc, tb):
                        pass

                self.conn.execute = MagicMock(return_value=ExecuteCM(self.row_val))

            async def __aenter__(cm_self):
                return cm_self.conn

            async def __aexit__(cm_self, *args):
                pass

        return AsyncCM(self.row_value)


@pytest.mark.asyncio
async def test_billing_middleware_success_db_lookup():
    # 1. Setup mocks
    api_key = "ctx_cloud_abcdef123"
    tenant_id = "tenant_test_123"

    mock_auth_result = AuthResult(
        authenticated=True, tenant_id=tenant_id, permissions=["write"], role="user"
    )

    mock_auth_manager = MagicMock()
    mock_auth_manager.authenticate_async = AsyncMock(return_value=mock_auth_result)

    mock_request = MagicMock(spec=Request)
    middleware = CortexBillingMiddleware(MagicMock())

    # 2. Patch AuthManager and AsyncStripeSyncer.queue_usage
    with (
        patch("babylon60.auth.manager.get_auth_manager", return_value=mock_auth_manager),
        patch(
            "babylon60.extensions.billing.metering.AsyncStripeSyncer.queue_usage",
            new_callable=AsyncMock,
        ) as mock_queue_call,
    ):
        await middleware._report_usage(api_key, mock_request)

        # 3. Assert queue_usage is called with ssu_cost=1
        mock_queue_call.assert_called_once_with(api_key, tenant_id, ssu_cost=1)


@pytest.mark.asyncio
async def test_billing_middleware_bypass_prevention_no_item_in_db(tmp_path: Path):
    # Directly test the AsyncStripeSyncer._report_batch function with database lookup
    from babylon60.extensions.billing.metering import AsyncStripeSyncer

    db_file = str(tmp_path / "billing_test.db")

    # Setup mock tenants table with no stripe_subscription_item_id
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE tenants (id TEXT PRIMARY KEY, config TEXT)")
    conn.execute("INSERT INTO tenants (id, config) VALUES ('tenant_no_stripe', '{}')")
    conn.commit()
    conn.close()

    # Patch DB_PATH in metering config
    from babylon60.core import config

    # We patch DB_PATH and stripe_lib
    mock_stripe_lib = MagicMock()
    mock_stripe_lib.api_key = "sk_live_prodkey"

    syncer = AsyncStripeSyncer()

    with (
        patch("babylon60.core.config.DB_PATH", db_file),
        patch.object(config, "STRIPE_SECRET_KEY", "sk_live_prodkey"),
    ):
        await syncer._report_batch(
            api_key="ctx_cloud_abcdef123",
            tenant_id="tenant_no_stripe",
            amount=10,
            stripe_lib=mock_stripe_lib,
        )

        # In production mode (not sk_test_mock), if no stripe subscription item ID exists,
        # it returns early and does NOT call SubscriptionItem.create_usage_record
        mock_stripe_lib.SubscriptionItem.create_usage_record.assert_not_called()
