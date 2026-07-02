"""
Unit tests for AsyncStripeSyncer in babylon60.extensions.billing.metering.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch
import pytest

from babylon60.extensions.billing.metering import get_stripe_syncer, AsyncStripeSyncer


@pytest.mark.asyncio
async def test_stripe_syncer_queue_usage():
    syncer = AsyncStripeSyncer()

    # Initially buffer should be empty
    assert len(syncer.usage_buffer) == 0

    # Queue some usage
    await syncer.queue_usage(api_key="key_1", tenant_id="tenant_a", ssu_cost=5)
    assert syncer.usage_buffer[("key_1", "tenant_a")] == 5

    await syncer.queue_usage(api_key="key_1", tenant_id="tenant_a", ssu_cost=3)
    assert syncer.usage_buffer[("key_1", "tenant_a")] == 8

    # Cancel background task to clean up
    if syncer._sync_task:
        syncer._sync_task.cancel()


@pytest.mark.asyncio
async def test_stripe_syncer_report_batch():
    syncer = AsyncStripeSyncer()
    mock_stripe = MagicMock()

    # Mock the database lookup to return a subscription item id
    with patch("sqlite3.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (
            json_data := '{"stripe_subscription_item_id": "si_123"}',
        )
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (json_data,)
        mock_connect.return_value.__enter__.return_value = mock_conn

        await syncer._report_batch(
            api_key="key_1", tenant_id="tenant_a", amount=10, stripe_lib=mock_stripe
        )

        # Verify Stripe API call
        mock_stripe.SubscriptionItem.create_usage_record.assert_called_once_with(
            "si_123", quantity=10, timestamp="now", action="increment"
        )
