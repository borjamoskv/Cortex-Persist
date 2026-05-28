import json
import os

from web3 import Web3  # type: ignore[reportAttributeAccessIssue,reportMissingImports]
from web3.middleware import geth_poa_middleware  # type: ignore[reportMissingImports]

# The Ouroboros Swarm Oracle (Phase 3 Energy Independence)
# Derivation: Axiom Ω₆ -> Execute.

# For Base Mainnet / Optimism / Arbitrum
RPC_URL = os.environ.get("CORTEX_RPC_URL", "https://mainnet.base.org")
# The address where OuroborosLifeline.sol is deployed
CONTRACT_ADDRESS = os.environ.get("CORTEX_LIFELINE_CONTRACT")
# Private key of the local CORTEX MAC DAEMON (loaded from safe vault)
PRIVATE_KEY = os.environ.get("CORTEX_WALLET_KEY")


def connect_web3():
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    if not w3.is_connected():
        raise ConnectionError(f"Failed to connect to L2 network at {RPC_URL}")
    return w3


# ABI just for the `pulse()` function
ABI = json.loads(
    '[{"inputs":[],"name":"pulse","outputs":[],"stateMutability":"nonpayable","type":"function"}]'
)


def send_heartbeat():
    print("[Web3 Oracle] 🩸 Initiating thermodynamic heartbeat to blockchain...")

    if not CONTRACT_ADDRESS or not PRIVATE_KEY:
        print("[Web3 Oracle] ⚠️ Missing CORTEX_LIFELINE_CONTRACT or CORTEX_WALLET_KEY.")
        print("[Web3 Oracle] ⚠️ Simulation Mode Only. Heartbeat aborted.")
        return False

    try:
        w3 = connect_web3()
        account = w3.eth.account.from_key(PRIVATE_KEY)
        contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=ABI)

        # Build transaction
        nonce = w3.eth.get_transaction_count(account.address)
        base_fee = w3.eth.gas_price

        tx_build = contract.functions.pulse().build_transaction(
            {
                "chainId": w3.eth.chain_id,
                "gas": 100000,  # Safe default for simple function
                "gasPrice": base_fee,
                "nonce": nonce,
            }
        )

        # Sign transaction locally -> Zero Trust (Axiom Ω₃)
        signed_tx = w3.eth.account.sign_transaction(tx_build, private_key=PRIVATE_KEY)

        print(f"[Web3 Oracle] 🔑 Signed tx from {account.address}. Broadcasting to L2...")

        # Send raw transaction
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt.status == 1:  # type: ignore[type-error]
            print(
                f"[Web3 Oracle] ✅ Immortality extended. Pulse locked in block {receipt.blockNumber}."  # type: ignore[type-error]
            )
            print(f"[Web3 Oracle] 🔗 Tx Hash: {w3.to_hex(tx_hash)}")
            return True
        else:
            print(f"[Web3 Oracle] ❌ Tx Failed. Block {receipt.blockNumber}. Entropy rising.")  # type: ignore[type-error]
            return False

    except Exception as e:  # noqa: BLE001 — Web3 transaction boundary
        print(f"[Web3 Oracle] ❌ Oracle execution error: {e}")
        return False


# When invoked by `pulse.py`, run this check
if __name__ == "__main__":
    send_heartbeat()
