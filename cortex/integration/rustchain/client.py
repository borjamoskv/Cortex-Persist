# [C5-REAL] Exergy-Maximized
"""RustChain RPC Async Client.

Handles interaction with the RustChain RPC network, supporting
fail-safe fallback and test mock mode.
"""

from __future__ import annotations

import hashlib
from typing import Any, Optional

import httpx


class RustChainClient:
    """Async client for RustChain node RPC."""

    def __init__(self, base_url: str = "https://50.28.86.131", mock_mode: bool = True) -> None:
        self.base_url = base_url.rstrip("/")
        self.mock_mode = mock_mode
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=5.0)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def health(self) -> dict[str, Any]:
        """Check the status of the node."""
        if self.mock_mode:
            return {"healthy": True, "epoch": 42, "version": "1.0.0"}
        try:
            client = await self.get_client()
            res = await client.get("/health")
            return res.json()
        except (ValueError, TypeError, OSError, KeyError) as e:
            return {"healthy": False, "error": str(e)}

    async def get_balance(self, address: str) -> dict[str, Any]:
        """Get balance for a wallet address."""
        if self.mock_mode:
            return {"address": address, "balance": 1000000, "nonce": 0}
        try:
            client = await self.get_client()
            res = await client.get(f"/wallet/balance?address={address}")
            return res.json()
        except Exception as e:
            raise ConnectionError(f"RustChain node connection failed: {e}")

    async def stake_rtc(
        self,
        from_address: str,
        amount: int,
        skill: str,
        signature: str,
        timestamp: int,
    ) -> dict[str, Any]:
        """Submit a staking transaction to lock RTC and acquire a skill."""
        if self.mock_mode:
            tx_hash = hashlib.sha256(
                f"{from_address}:{amount}:{skill}:{timestamp}".encode()
            ).hexdigest()
            attestation = {
                "verdict": "approved",
                "skill": skill,
                "amount": amount,
                "staker": from_address,
                "tx_hash": tx_hash,
                "timestamp": timestamp,
            }
            return {
                "status": "success",
                "tx_hash": tx_hash,
                "attestation": attestation,
                "gate_signature": "mock_gate_signature_bytes_hex",
            }

        try:
            client = await self.get_client()
            res = await client.post(
                "/stake",
                json={
                    "from": from_address,
                    "amount": amount,
                    "skill": skill,
                    "signature": signature,
                    "timestamp": timestamp,
                },
            )
            res.raise_for_status()
            return res.json()
        except Exception as e:
            raise ConnectionError(f"RustChain staking failed: {e}")
