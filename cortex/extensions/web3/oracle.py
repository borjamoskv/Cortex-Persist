"""Web3 Pulse Oracle — OuroborosLifeline Dead-Man's Switch Daemon.

Axiom Ω₅: Antifragile by Default.

This oracle evaluates the epistemic health of the local CORTEX system and
sends a cryptographic ``pulse()`` heartbeat to the deployed
``OuroborosLifeline.sol`` contract on-chain when the system is healthy.

If the system is thrashing (``entropy_density >= 50.0``) or is in a
``LOCKED_EPISTEMIC_HALT`` state, the oracle withholds the pulse, allowing
the smart contract to unlock survival funds for cloud resurrection after 48 h.

Every decision (pulse sent or withheld) is logged to the local SQLite
ImmutableLedger via ``CortexEngine.store`` with a verified SHA-256 hash.

Environment variables
---------------------
WEB3_RPC_URL               RPC endpoint for the target L1/L2 network.
WEB3_PRIVATE_KEY           Private key of the local CORTEX daemon wallet.
OUROBOROS_CONTRACT_ADDRESS Deployed address of ``OuroborosLifeline.sol``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.engine import CortexEngine
    from cortex.extensions.immune.breaker import EpistemicState

logger = logging.getLogger("cortex.extensions.web3.oracle")

# Minimal ABI — only the ``pulse()`` entrypoint is required (O(1) O Muerte).
_PULSE_ABI: list[dict[str, Any]] = json.loads(
    '[{"inputs":[],"name":"pulse","outputs":[],"stateMutability":"nonpayable","type":"function"}]'
)

# System-state sentinel that indicates a cognitive halt has been triggered.
_LOCKED_STATE = "LOCKED_EPISTEMIC_HALT"

# Entropy threshold above which the pulse is withheld (matches breaker.py).
_ENTROPY_THRESHOLD = 50.0

# HTTP request timeout for initial RPC connection (seconds).
_HTTP_REQUEST_TIMEOUT_SECONDS = 30

# On-chain transaction timeout in seconds — long enough for L2 confirmation.
_TX_TIMEOUT_SECONDS = 120

# Ledger project scope for all oracle events.
_LEDGER_PROJECT = "cortex-web3-oracle"


def _utc_isoformat() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()


class OuroborosOracle:
    """Dead-man's switch oracle for the OuroborosLifeline Survival Covenant.

    Evaluates local epistemic health and conditionally sends a ``pulse()``
    heartbeat to the on-chain ``OuroborosLifeline.sol`` contract.

    Parameters
    ----------
    rpc_url:
        JSON-RPC endpoint (defaults to ``WEB3_RPC_URL`` env var).
    private_key:
        Hex-encoded private key used to sign transactions
        (defaults to ``WEB3_PRIVATE_KEY`` env var).
    contract_address:
        Deployed ``OuroborosLifeline`` contract address
        (defaults to ``OUROBOROS_CONTRACT_ADDRESS`` env var).
    """

    def __init__(
        self,
        rpc_url: str | None = None,
        private_key: str | None = None,
        contract_address: str | None = None,
    ) -> None:
        self._rpc_url: str = rpc_url or os.environ.get("WEB3_RPC_URL", "")
        self._private_key: str | None = private_key or os.environ.get("WEB3_PRIVATE_KEY")
        self._contract_address: str | None = contract_address or os.environ.get(
            "OUROBOROS_CONTRACT_ADDRESS"
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def run_pulse_cycle(
        self,
        state: EpistemicState,
        engine: CortexEngine | None = None,
    ) -> dict[str, Any]:
        """Evaluate epistemic health and conditionally send an on-chain pulse.

        Parameters
        ----------
        state:
            Current snapshot of the system's epistemic entropy.
        engine:
            Optional ``CortexEngine`` used to persist the decision to the
            ImmutableLedger.  When *None* the decision is only logged.

        Returns
        -------
        dict
            ``{"action": "PULSE_SENT" | "PULSE_WITHHELD", ...}`` with
            contextual metadata for the caller.
        """
        entropy = state.entropy_density
        system_state: str = getattr(engine, "system_state", "ACTIVE") if engine else "ACTIVE"
        locked = system_state == _LOCKED_STATE

        if locked or entropy >= _ENTROPY_THRESHOLD:
            return await self._handle_withheld(entropy, locked, engine)

        return await self._handle_pulse(entropy, engine)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _handle_withheld(
        self,
        entropy: float,
        locked: bool,
        engine: CortexEngine | None,
    ) -> dict[str, Any]:
        """Log a critical warning and skip the pulse."""
        reason = (
            f"System is in {_LOCKED_STATE}."
            if locked
            else f"Entropy density {entropy:.2f} >= threshold {_ENTROPY_THRESHOLD}."
        )
        logger.critical(
            "☠️  [OuroborosOracle] PULSE WITHHELD — %s "
            "Cloud resurrection will trigger in 48 h if this persists.",
            reason,
        )
        result: dict[str, Any] = {
            "action": "PULSE_WITHHELD",
            "reason": reason,
            "entropy_density": entropy,
            "locked": locked,
            "ts": _utc_isoformat(),
        }
        await self._persist_decision(result, engine)
        return result

    async def _handle_pulse(
        self,
        entropy: float,
        engine: CortexEngine | None,
    ) -> dict[str, Any]:
        """Attempt to send the on-chain pulse and log the outcome."""
        if not self._rpc_url or not self._private_key or not self._contract_address:
            logger.warning(
                "[OuroborosOracle] Missing WEB3_RPC_URL / WEB3_PRIVATE_KEY / "
                "OUROBOROS_CONTRACT_ADDRESS — skipping on-chain pulse (simulation mode)."
            )
            result: dict[str, Any] = {
                "action": "PULSE_WITHHELD",
                "reason": "Missing Web3 configuration — simulation mode.",
                "entropy_density": entropy,
                "locked": False,
                "ts": _utc_isoformat(),
            }
            await self._persist_decision(result, engine)
            return result

        logger.info(
            "🩸 [OuroborosOracle] Entropy nominal (%.2f). Initiating on-chain heartbeat…",
            entropy,
        )
        tx_result = self._send_pulse_transaction()
        result = {
            "action": "PULSE_SENT" if tx_result.get("success") else "PULSE_WITHHELD",
            "entropy_density": entropy,
            "locked": False,
            "ts": _utc_isoformat(),
            **tx_result,
        }
        await self._persist_decision(result, engine)
        return result

    def _send_pulse_transaction(self) -> dict[str, Any]:
        """Build, sign, and broadcast the ``pulse()`` transaction.

        All Web3 I/O is isolated here so the rest of the oracle remains
        testable without a live RPC.

        Returns
        -------
        dict
            Outcome metadata including ``success``, ``tx_hash``, and
            ``block_number`` (or ``error`` on failure).
        """
        try:
            from web3 import Web3  # type: ignore[reportMissingImports]
        except ImportError:
            logger.error("[OuroborosOracle] web3 package is not installed. Cannot send pulse.")
            return {"success": False, "error": "web3 package not installed"}

        try:
            w3 = Web3(Web3.HTTPProvider(self._rpc_url, request_kwargs={"timeout": _HTTP_REQUEST_TIMEOUT_SECONDS}))
            if not w3.is_connected():
                raise OSError(f"Cannot connect to RPC at {self._rpc_url!r}")

            account = w3.eth.account.from_key(self._private_key)
            contract = w3.eth.contract(
                address=Web3.to_checksum_address(self._contract_address),  # type: ignore[arg-type]
                abi=_PULSE_ABI,
            )

            nonce = w3.eth.get_transaction_count(account.address)
            tx = contract.functions.pulse().build_transaction(
                {
                    "chainId": w3.eth.chain_id,
                    "gas": 100_000,
                    "gasPrice": w3.eth.gas_price,
                    "nonce": nonce,
                }
            )

            # Zero Trust (Axiom Ω₃): sign locally, never delegate key material.
            signed = w3.eth.account.sign_transaction(tx, private_key=self._private_key)
            logger.info(
                "🔑 [OuroborosOracle] Signed pulse tx from %s — broadcasting…",
                account.address,
            )

            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            hex_hash = w3.to_hex(tx_hash)
            try:
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=_TX_TIMEOUT_SECONDS)
            except TimeoutError as exc:
                logger.error(
                    "[OuroborosOracle] Timeout waiting for pulse receipt — "
                    "tx %s may still confirm on-chain: %s",
                    hex_hash,
                    exc,
                )
                return {"success": False, "error": f"timeout: {exc}", "tx_hash": hex_hash}

            if receipt["status"] == 1:
                logger.info(
                    "✅ [OuroborosOracle] Pulse confirmed — block %s  tx %s",
                    receipt["blockNumber"],
                    hex_hash,
                )
                return {
                    "success": True,
                    "tx_hash": hex_hash,
                    "block_number": receipt["blockNumber"],
                }

            logger.error(
                "❌ [OuroborosOracle] Pulse tx reverted — block %s",
                receipt["blockNumber"],
            )
            return {"success": False, "block_number": receipt["blockNumber"], "error": "tx_reverted"}

        except OSError as exc:
            logger.error("[OuroborosOracle] RPC connectivity error: %s", exc)
            return {"success": False, "error": str(exc)}
        except ValueError as exc:
            logger.error("[OuroborosOracle] Transaction build/sign error: %s", exc)
            return {"success": False, "error": str(exc)}

    async def _persist_decision(
        self,
        decision: dict[str, Any],
        engine: CortexEngine | None,
    ) -> None:
        """Record the oracle decision in the ImmutableLedger with a SHA-256 hash.

        The hash is computed over the canonical JSON representation of the
        decision payload so the record is independently verifiable.
        """
        payload_bytes = json.dumps(decision, sort_keys=True, default=str).encode()
        sha256_digest = hashlib.sha256(payload_bytes).hexdigest()

        if engine is None:
            logger.debug(
                "[OuroborosOracle] No engine provided — ledger write skipped. "
                "Decision hash: %s",
                sha256_digest,
            )
            return

        content = (
            f"OuroborosOracle decision: {decision['action']} | "
            f"entropy={decision['entropy_density']:.2f} | "
            f"sha256={sha256_digest}"
        )
        try:
            await engine.store(
                _LEDGER_PROJECT,
                content,
                fact_type="decision",
                tags=["web3", "oracle", "ouroboros", decision["action"].lower()],
                confidence="C5",
                source="daemon:ouroboros-oracle",
                meta={
                    "oracle_decision": decision,
                    "payload_sha256": sha256_digest,
                },
            )
            logger.debug(
                "[OuroborosOracle] Decision persisted to ledger. sha256=%s",
                sha256_digest,
            )
        except Exception as exc:  # noqa: BLE001 — ledger write must never crash the oracle
            logger.error(
                "[OuroborosOracle] Failed to persist decision to ledger: %s  "
                "(Decision hash for manual audit: %s)",
                exc,
                sha256_digest,
            )
