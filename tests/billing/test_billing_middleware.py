# [C5-REAL] Exergy-Maximized Stripe Billing Middleware tests
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts" / "lab"))

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import Request
from cortex.api.middleware import CortexBillingMiddleware
from cortex.auth.models import AuthResult

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
                        cursor.fetchone.return_value = (self.r_val,) if self.r_val is not None else None
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
    sub_item_id = "si_prod_item_999"

    mock_auth_result = AuthResult(
        authenticated=True,
        tenant_id=tenant_id,
        permissions=["write"],
        role="user"
    )

    mock_auth_manager = MagicMock()
    mock_auth_manager.authenticate_async = AsyncMock(return_value=mock_auth_result)

    mock_request = MagicMock(spec=Request)
    mock_pool = FakePool(json.dumps({"stripe_subscription_item_id": sub_item_id}))
    mock_request.app.state.pool = mock_pool

    middleware = CortexBillingMiddleware(MagicMock())

    # 2. Patch AuthManager and stripe to simulate production mode
    with patch("cortex.auth.manager.get_auth_manager", return_value=mock_auth_manager), \
         patch("stripe.SubscriptionItem.create_usage_record", create=True) as mock_stripe_call:
        
        # Inject STRIPE_SECRET_KEY
        from cortex.core import config
        with patch.object(config, "STRIPE_SECRET_KEY", "sk_live_prodkey"):
            await middleware._report_usage(api_key, mock_request)

        # 3. Assert stripe call is made with the ID fetched from the database config
        mock_stripe_call.assert_called_once_with(
            sub_item_id,
            quantity=1,
            timestamp="now",
            action="increment"
        )


@pytest.mark.asyncio
async def test_billing_middleware_bypass_prevention_no_item_in_db():
    # Verify that if no stripe_subscription_item_id is in DB, it returns early and does NOT call Stripe.
    api_key = "ctx_cloud_abcdef123"
    tenant_id = "tenant_test_123"

    mock_auth_result = AuthResult(
        authenticated=True,
        tenant_id=tenant_id,
        permissions=["write"],
        role="user"
    )

    mock_auth_manager = MagicMock()
    mock_auth_manager.authenticate_async = AsyncMock(return_value=mock_auth_result)

    mock_request = MagicMock(spec=Request)
    mock_pool = FakePool(json.dumps({})) # Empty config
    mock_request.app.state.pool = mock_pool

    middleware = CortexBillingMiddleware(MagicMock())

    with patch("cortex.auth.manager.get_auth_manager", return_value=mock_auth_manager), \
         patch("stripe.SubscriptionItem.create_usage_record", create=True) as mock_stripe_call:
        
        from cortex.core import config
        with patch.object(config, "STRIPE_SECRET_KEY", "sk_live_prodkey"):
            await middleware._report_usage(api_key, mock_request)

        # Assert no stripe call is made
        mock_stripe_call.assert_not_called()
