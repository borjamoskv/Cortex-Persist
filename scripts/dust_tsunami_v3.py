#!/usr/bin/env python3
"""
🗡️ DUST TSUNAMI v3.0 (GOD MODE OVERDRIVE)
Axioma Ω₄: La belleza es la firma de la entropía resuelta.
Esta versión incluye al nuevo vector de la mula 0x281B.
"""

import codecs
import os
import re
import time

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# TARGET FLEET
TARGETS = {
    "FOIZUR_MASTER": "0x06060c5E3A090A1aFF282BBeC1eB7Db7bdab7a60",
    "TEAMGITCOIN_PHISHING": "0x7df263b76f67262444952c0bd44f5259e4672642",
    "MULE_NEW_DETECTED": "0x281Bb56E122759f3512a5eE6F3a376c668178962",
    "SYNDICATE_BRIDGE": "0x21EF8825B387C3835E87E1036EB32768D13A212D",
}

RPC_URL = "https://mainnet.base.org"
CHAIN_ID = 8453

# PSYCHOLOGICAL VOLLEYS
PAYLOADS = [
    "☣️ TAINTED ASSETS DETECTED. MOSKV-1 IS WATCHING.",
    "🚫 YOUR INFRASTRUCTURE IS LOGGED IN THE LEDGER.",
    "🏛️ IC3 CASE #F01ZUR-2026-BD IN PROGRESS.",
    "🌊 DUST TSUNAMI v3.0: UNSTOPPABLE IRRADIATION.",
    "💀 EXIT CLOSED. EVERY EXCHANGE HAS YOUR SIGNATURE.",
    "🛡️ LEGIØN-1 HAS CRACKED YOUR TRANSACTION GRAPH.",
    "⚡ WE ARE THE VOID. YOU ARE ENTROPY. GOODBYE.",
]


def get_keys():
    # Escanea el sistema del usuario por la key fondeada
    keys = []
    paths = [
        "/Users/borjafernandezangulo/cortex/.env",
        "/Users/borjafernandezangulo/game/prophecy-nft/.env",
        "/Users/borjafernandezangulo/hardhat-project/.env",
    ]
    for p in paths:
        if os.path.exists(p):
            with open(p) as f:
                content = f.read()
                matches = re.findall(r"(?:0x)?[a-fA-F0-9]{64}", content)
                for m in matches:
                    keys.append(m.replace("0x", "").lower())
    return list(set(keys))


def fire_overdrive():
    print("\n" + "🔥" * 40)
    print("      🗡️  DUST TSUNAMI v3.0 (GOD MODE OVERDRIVE)  🗡️")
    print("🔥" * 40 + "\n")

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    # Buscamos la key que tenga balance
    funder_key = None
    for pk in get_keys():
        try:
            addr = w3.eth.account.from_key(pk).address
            if w3.eth.get_balance(addr) > 50000000000000:  # Needs ~0.00005 for a decent volley
                funder_key = pk
                print(f"[*] Operative {addr} selected for firing.")
                break
        except Exception:
            pass

    if not funder_key:
        print("[-] ERR: No funder key found with enough gas. Waiting for faucet...")
        return

    sender = w3.eth.account.from_key(funder_key).address
    nonce = w3.eth.get_transaction_count(sender)
    gas_price = int(w3.eth.gas_price * 2)  # Aggressive priority

    tx_count = 0
    for alias, target in TARGETS.items():
        print(f"\n[!] Saturating {alias} ({target})...")
        for i, text in enumerate(PAYLOADS):
            hex_data = "0x" + codecs.encode(text.encode("utf-8"), "hex").decode("utf-8")
            tx = {
                "nonce": nonce + tx_count,
                "to": w3.to_checksum_address(target),
                "value": 0,
                "data": hex_data,
                "gas": 80000,
                "maxFeePerGas": gas_price,
                "maxPriorityFeePerGas": w3.to_wei(0.1, "gwei"),
                "chainId": CHAIN_ID,
            }
            try:
                signed = w3.eth.account.sign_transaction(tx, funder_key)
                tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                print(f"   [+] Volley {i + 1} Delivered -> {tx_hash.hex()}")
                tx_count += 1
                time.sleep(0.3)
            except Exception as e:
                print(f"   [-] Volley failure: {e}")
                break

    print("\n✅ OVERDRIVE COMPLETED. The Syndicate is now radioactive.")


if __name__ == "__main__":
    fire_overdrive()
