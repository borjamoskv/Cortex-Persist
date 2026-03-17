"""MOSKV-Aether — CDP AgentKit Sovereign Wallet.

[SOVEREIGN WALLET V3.0] - Axioma Ω₅ (Antifragile by Default)
Integración CORTEX con Coinbase Developer Platform.
Singleton: una única instancia por proceso.
"""

from __future__ import annotations

import asyncio
import logging
import os
import stat
from decimal import Decimal
from typing import Any

try:
    from cdp_langchain.agent_toolkits import CdpToolkit  # pyright: ignore[reportMissingImports]
    from cdp_langchain.utils import CdpAgentkitWrapper  # pyright: ignore[reportMissingImports]

    CDP_AVAILABLE = True
except ImportError:
    CDP_AVAILABLE = False

    class CdpAgentkitWrapper:
        wallet: Any

        def __init__(self, **kwargs: Any) -> None:
            pass

        def export_wallet(self) -> str:
            return ""

    class _MockCdpToolkit:
        def get_tools(self) -> list[Any]:
            return []

    class CdpToolkit:
        @classmethod
        def from_cdp_agentkit_wrapper(cls, wrapper: Any) -> _MockCdpToolkit:
            return _MockCdpToolkit()


logger = logging.getLogger(__name__)

# ── Spending Guardrails (Axiom Ω₃: Verify, then trust) ──────────
MAX_TX_AMOUNT = Decimal("1.0")  # Max per-transaction (ETH equiv)
MAX_TX_PER_SESSION = 10  # Circuit breaker per boot cycle
_tx_count_this_session = 0


class CDPSovereignWallet:
    """Singleton Sovereign Wallet — O(1) initialization, persistent identity.

    Uses CdpAgentkitWrapper from cdp-langchain for MPC wallet management.
    Wallet seed persists to ~/.cortex/ with restricted file permissions (0600).
    """

    _instance: CDPSovereignWallet | None = None
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        """Singleton pattern — one wallet per process."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        network_id: str = "base-sepolia",
        seed_path: str = "~/.cortex/agent_wallet_seed.json",
    ):
        if CDPSovereignWallet._initialized:
            return
        self.network_id = network_id
        self.seed_path = os.path.expanduser(seed_path)
        self.api_key_name = os.getenv("CDP_API_KEY_NAME", "")
        self.private_key = os.getenv("CDP_API_KEY_PRIVATE_KEY", "").replace("\\n", "\n")
        self.agentkit: CdpAgentkitWrapper | None = None
        self.tools: list[Any] = []

        if not CDP_AVAILABLE:
            logger.warning("cdp-langchain not installed. Sovereign Wallet in stub-mode.")

    def initialize(self) -> bool:
        """Initialize the MPC wallet, restoring or creating seed."""
        if CDPSovereignWallet._initialized and self.agentkit:
            return True

        if not CDP_AVAILABLE:
            logger.error("[CDP] cdp-langchain not installed.")
            return False

        if not self.api_key_name or not self.private_key:
            logger.error("[CDP] Missing CDP_API_KEY_NAME or CDP_API_KEY_PRIVATE_KEY in ENV.")
            return False

        wallet_data = None
        if os.path.exists(self.seed_path):
            try:
                with open(self.seed_path) as f:
                    wallet_data = f.read()
                logger.info(
                    "[CDP] Restoring seed from %s",
                    self.seed_path,
                )
            except OSError as e:
                logger.error("[CDP] Seed read failed, creating new: %s", e)

        try:
            self.agentkit = CdpAgentkitWrapper(
                cdp_api_key_name=self.api_key_name,
                cdp_api_key_private_key=self.private_key,
                network_id=self.network_id,
                cdp_wallet_data=wallet_data,
            )
            assert self.agentkit is not None

            # Persist seed with restrictive permissions (0600)
            new_wallet_data = self.agentkit.export_wallet()
            if new_wallet_data and new_wallet_data != wallet_data:
                self._write_seed(new_wallet_data)

            # Load LangChain action tools
            cdp_toolkit = CdpToolkit.from_cdp_agentkit_wrapper(
                self.agentkit,
            )
            self.tools = cdp_toolkit.get_tools()
            CDPSovereignWallet._initialized = True
            logger.info(
                "[CDP] Wallet initialized (%d tools loaded)",
                len(self.tools),
            )
            return True

        except ValueError as e:
            logger.error("[CDP] Config error: %s", e)
            return False
        except ConnectionError as e:
            logger.error("[CDP] Network error: %s", e)
            return False
        except RuntimeError as e:
            logger.error("[CDP] Runtime error: %s", e)
            return False

    def _write_seed(self, data: str) -> None:
        """Write seed file with 0600 permissions (owner-only)."""
        seed_dir = os.path.dirname(self.seed_path)
        if seed_dir:
            os.makedirs(seed_dir, exist_ok=True)
        with open(self.seed_path, "w") as f:
            f.write(data)
        os.chmod(self.seed_path, stat.S_IRUSR | stat.S_IWUSR)
        logger.info("[CDP] Seed persisted (0600): %s", self.seed_path)

    async def get_balance(self, asset: str = "eth") -> str:
        """Return balance for the given asset."""
        if not self.agentkit:
            return "0.0"
        try:
            assert self.agentkit is not None
            wallet = self.agentkit.wallet
            loop = asyncio.get_running_loop()
            balance = await loop.run_in_executor(
                None,
                wallet.balance,
                asset,
            )
            return str(balance)
        except AttributeError as e:
            logger.error("[CDP] Wallet attribute error: %s", e)
            return "0.0"
        except ConnectionError as e:
            logger.error("[CDP] Network error on balance: %s", e)
            return "0.0"

    async def fund_subagent(
        self,
        target_address: str,
        amount: str,
        asset: str = "usdc",
    ) -> bool:
        """Transfer funds to a subagent address.

        Guarded by MAX_TX_AMOUNT and MAX_TX_PER_SESSION.
        """
        global _tx_count_this_session

        if not self.agentkit:
            logger.error("[CDP] Wallet not initialized.")
            return False

        # ── Spending Guardrails ──────────────────────────────
        tx_amount = Decimal(amount)
        if tx_amount > MAX_TX_AMOUNT:
            logger.error(
                "[CDP] TX BLOCKED: %s exceeds MAX_TX_AMOUNT (%s)",
                amount,
                MAX_TX_AMOUNT,
            )
            return False

        if _tx_count_this_session >= MAX_TX_PER_SESSION:
            logger.error(
                "[CDP] TX BLOCKED: Session limit reached (%d/%d)",
                _tx_count_this_session,
                MAX_TX_PER_SESSION,
            )
            return False

        if not target_address.startswith("0x") or len(target_address) != 42:
            logger.error(
                "[CDP] TX BLOCKED: Invalid address format: %s",
                target_address,
            )
            return False

        logger.info(
            "[CDP TX] %s %s -> %s",
            amount,
            asset.upper(),
            target_address,
        )

        def _transfer() -> Any:
            assert self.agentkit is not None
            wallet = self.agentkit.wallet
            t = wallet.transfer(amount, asset, target_address)
            t.wait()
            return t

        try:
            await asyncio.to_thread(_transfer)
            _tx_count_this_session += 1
            logger.info(
                "[CDP TX CONFIRMED] %d/%d this session",
                _tx_count_this_session,
                MAX_TX_PER_SESSION,
            )
            return True
        except ValueError as e:
            logger.error("[CDP] Transfer value error: %s", e)
            return False
        except ConnectionError as e:
            logger.error("[CDP] Transfer network error: %s", e)
            return False
        except RuntimeError as e:
            logger.error("[CDP] Transfer runtime error: %s", e)
            return False


if __name__ == "__main__":

    async def run_wallet_test():
        print("--- Testing CDP Sovereign Wallet V3 ---")
        wallet = CDPSovereignWallet(network_id="base-sepolia")
        success = wallet.initialize()

        if success:
            balance = await wallet.get_balance("eth")
            print(f"✅ Wallet OK. Balance: {balance} ETH")
            print(f"   Tools loaded: {len(wallet.tools)}")
            for t in wallet.tools:
                desc = t.description[:70]
                print(f"   - {t.name}: {desc}...")

            # Verify singleton
            w2 = CDPSovereignWallet()
            assert w2 is wallet, "Singleton broken!"
            print("✅ Singleton verified")
        else:
            print("❌ Init failed. Check ENVs and deps.")

    asyncio.run(run_wallet_test())
