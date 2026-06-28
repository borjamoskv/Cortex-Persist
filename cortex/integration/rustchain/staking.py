# [C5-REAL] Exergy-Maximized
"""RustChain Staking Logic.

Handles staking transactions and fail-safe logic when node is offline.
"""

from __future__ import annotations

import time
from typing import Any

from cortex.integration.rustchain.client import RustChainClient
from cortex.integration.rustchain.wallet import RustChainWallet


class StakingError(Exception):
    """Base exception for staking operations."""

    pass


class GateUnavailableError(StakingError):
    """Raised when the staking gate or node is offline/unhealthy."""

    pass


async def stake_and_acquire(
    wallet: RustChainWallet,
    client: RustChainClient,
    skill: str,
    amount: int,
) -> dict[str, Any]:
    """Lock RTC stake to acquire a skill.

    Fail-safe: performs pre-flight client check. If connection is offline,
    it raises GateUnavailableError to avoid state loss.
    """
    # 1. Health check
    try:
        health = await client.health()
        if not health.get("healthy", False):
            raise GateUnavailableError("RustChain gate is unhealthy or offline")
    except Exception as e:
        if isinstance(e, GateUnavailableError):
            raise
        raise GateUnavailableError(f"RustChain health check failed: {e}")

    # 2. Sign transaction payload
    timestamp = int(time.time())
    payload = f"{wallet.address}:{amount}:{skill}:{timestamp}".encode()
    signature_bytes = wallet.sign(payload)
    signature_hex = signature_bytes.hex()

    # 3. Submit staking transaction
    try:
        receipt = await client.stake_rtc(
            from_address=wallet.address,
            amount=amount,
            skill=skill,
            signature=signature_hex,
            timestamp=timestamp,
        )
        if receipt.get("status") != "success":
            raise StakingError(
                f"Staking transaction rejected: {receipt.get('error', 'unknown error')}"
            )
        return receipt
    except Exception as e:
        if isinstance(e, StakingError):
            raise
        raise StakingError(f"Failed to submit staking transaction: {e}")
