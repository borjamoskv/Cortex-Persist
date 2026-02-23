"""Sentinel Monitor for threat actor tracking via pure HTTP."""

import asyncio
import logging
import os
import sys
from typing import Any

import aiohttp

logger = logging.getLogger("cortex.sentinel")

TARGET_ADDRESS = "0x0083022683E56a51Ef1199573411ba6c2ab60000"
ETHERSCAN_API_URL = "https://api.etherscan.io/api"


class SentinelMonitor:
    """Watches the threat actor's wallet for movements outward."""

    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.last_block_scanned = 0
        self.is_running = False

    async def _notify_os(self, title: str, message: str) -> None:
        """Trigger an OS notification (macOS, Linux, Windows) to break focus modes."""
        try:
            if sys.platform == "darwin":
                script = f'display notification "{message}" with title "{title}" sound name "Basso"'
                proc = await asyncio.create_subprocess_exec(
                    "osascript",
                    "-e",
                    script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
            elif sys.platform.startswith("linux"):
                proc = await asyncio.create_subprocess_exec(
                    "notify-send",
                    title,
                    message,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
            elif sys.platform == "win32":
                ps_script = f"(New-Object -ComObject Wscript.Shell).Popup('{message}', 10, '{title}', 0x0 + 0x30)"
                proc = await asyncio.create_subprocess_exec(
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    ps_script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
        except Exception as e:
            logger.error(f"Failed to send OS notification on {sys.platform}: {e}")

    def _log_fact(self, tx_hash: str, to_addr: str, value: str, asset: str) -> None:
        """Store a high-priority Fact in CORTEX about the movement."""
        try:
            from cortex.engine.sync_write import store_fact_sync

            content = (
                f"SENTINEL ALERT: Threat Actor `{TARGET_ADDRESS}` moved `{value}` "
                f"of `{asset}`\\n"
                f"Destination: `{to_addr}`\\n"
                f"TxHash: `{tx_hash}`"
            )
            store_fact_sync(
                "cortex",
                content,
                fact_type="security_alert",
                tags=["sentinel", "critical", "threat_actor"],
                confidence="verified",
                meta={"tx_hash": tx_hash, "from": TARGET_ADDRESS, "to": to_addr, "value": value},
            )
        except Exception as e:
            logger.error(f"Failed to store sentinel fact: {e}")

    async def _fetch_txlist(
        self, session: aiohttp.ClientSession, action: str
    ) -> list[dict[str, Any]]:
        api_key = os.environ.get("ETHERSCAN_API_KEY", "")
        # Use Etherscan API format
        params = {
            "module": "account",
            "action": action,
            "address": TARGET_ADDRESS,
            "startblock": self.last_block_scanned + 1,
            "endblock": 99999999,
            "sort": "asc",
            "apikey": api_key,
        }
        try:
            async with session.get(ETHERSCAN_API_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "1" and isinstance(data.get("result"), list):
                        return data["result"]
        except Exception as e:
            logger.warning(f"Fetch failed for {action}: {e}")
        return []

    async def _check_movements(self, session: aiohttp.ClientSession) -> None:
        """Poll the API for new transactions."""
        normal_txs = await self._fetch_txlist(session, "txlist")
        token_txs = await self._fetch_txlist(session, "tokentx")

        # Combine and sort by block number
        all_txs = sorted(normal_txs + token_txs, key=lambda x: int(x.get("blockNumber", 0)))

        highest_block = self.last_block_scanned

        for tx in all_txs:
            block_num = int(tx.get("blockNumber", 0))
            if block_num > highest_block:
                highest_block = block_num

            from_addr = tx.get("from", "").lower()
            if from_addr == TARGET_ADDRESS.lower():
                # Outbound translation detected!
                to_addr = tx.get("to", "Unknown")
                tx_hash = tx.get("hash", "Unknown")

                # Determine asset and value
                if "tokenSymbol" in tx:
                    asset = tx["tokenSymbol"]
                    decimals = int(tx.get("tokenDecimal", 18))
                    raw_val = float(tx.get("value", 0))
                    value = f"{raw_val / (10**decimals):.4f}"
                else:
                    asset = "ETH"
                    raw_val = float(tx.get("value", 0))
                    value = f"{raw_val / (10**18):.4f}"

                msg = f"Movement Detected! {value} {asset} sent to {to_addr}"
                logger.critical(f"SENTINEL ALERT: {msg} (Tx: {tx_hash})")

                await self._notify_os("⚠️ CORTEX SENTINEL ALERT ⚠️", msg)
                self._log_fact(tx_hash, to_addr, value, asset)

        self.last_block_scanned = highest_block

    async def run_loop(self) -> None:
        """Main async loop."""
        self.is_running = True
        logger.info(f"Sentinel Monitor started for {TARGET_ADDRESS}")

        # If we start from 0, we might get thousands of historical txs.
        # In a real scenario, we'd initialize this to the current block.
        # For this implementation, we assume we just want to watch forward,
        # but Etherscan API is pagination-based.
        # We'll just fetch once to establish the baseline block.
        api_key = os.environ.get("ETHERSCAN_API_KEY", "")
        async with aiohttp.ClientSession() as session:
            # Get latest block as baseline
            try:
                params = {"module": "proxy", "action": "eth_blockNumber", "apikey": api_key}
                async with session.get(ETHERSCAN_API_URL, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("result"):
                            self.last_block_scanned = int(data["result"], 16)
                            logger.info(
                                f"Sentinel baseline established at block {self.last_block_scanned}"
                            )
            except Exception as e:
                logger.warning(f"Could not establish baseline block: {e}")

            while self.is_running:
                try:
                    await self._check_movements(session)
                except asyncio.CancelledError:
                    self.is_running = False
                    raise
                except Exception as e:
                    logger.error(f"Error in Sentinel loop: {e}")

                await asyncio.sleep(self.check_interval)
