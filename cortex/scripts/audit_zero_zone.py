import os

import requests
from dotenv import load_dotenv

load_dotenv()

ALCHEMY_KEY = os.getenv("ALCHEMY_API_KEY", "DEMO_KEY")

ZERO_ZONE_WALLET = "0x5247299421A3Ff724c41582E5A44c6551d135Fd3"

CHAINS = {
    "ETH": f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}",
    "BASE": f"https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}",
    "ARB": f"https://arb-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}",
    "OP": f"https://opt-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}",
}

print("============================================================")
print(f" 🔍 AUDITORÍA DE LA ZONA CERO: {ZERO_ZONE_WALLET}")
print("============================================================")

for chain_name, rpc_url in CHAINS.items():
    print(f"\n--- SCANNING {chain_name} ---")

    # Check ETH/Native balance
    payload_eth = {
        "jsonrpc": "2.0",
        "method": "eth_getBalance",
        "params": [ZERO_ZONE_WALLET, "latest"],
        "id": 1,
    }

    try:
        res = requests.post(rpc_url, json=payload_eth)
        balance_wei = int(res.json().get("result", "0x0"), 16)
        balance_eth = balance_wei / 10**18
        print(f"🪙  Native Balance: {balance_eth:.6f}")
    except Exception as e:
        print(f"⚠️ Error getBalance: {e}")

    # Check ERC20 balances
    payload_tokens = {
        "jsonrpc": "2.0",
        "method": "alchemy_getTokenBalances",
        "params": [ZERO_ZONE_WALLET],
        "id": 1,
    }

    try:
        res = requests.post(rpc_url, json=payload_tokens)
        tokens = res.json().get("result", {}).get("tokenBalances", [])

        non_zero = [t for t in tokens if int(t["tokenBalance"], 16) > 0]
        if non_zero:
            print(f"📦 ERC20 Tokens con balance: {len(non_zero)}")
            for t in non_zero:
                print(f"   - Contr: {t['contractAddress']} | Bal(Hex): {t['tokenBalance']}")
        else:
            print("📦 Sin tokens ERC20 detectados.")
    except Exception as e:
        print(f"⚠️ Error getTokenBalances: {e}")

print("\n============================================================")
print(" Auditoría completada. Si hay tokens valiosos, armar Rescate MEV.")
