#!/usr/bin/env python3
"""
👁️ MOSKV-PANOPTICON v1.0
Daemon de Vigilancia On-Chain.
Axioma Ω₁: Causalidad Multi-Escala.
"""

import subprocess
import time

from web3 import Web3

# FLOTA IDENTIFICADA
W3_TEMP = Web3()
TARGETS = {
    "FOIZUR_MASTER": W3_TEMP.to_checksum_address("0x06060c5E3A090A1aFF282BBeC1eB7Db7bdab7a60"),
    "TEAMGITCOIN_BASE": W3_TEMP.to_checksum_address("0x7df263b76f67262444952c0bd44f5259e4672642"),
    "MULE_TIER_2": W3_TEMP.to_checksum_address("0xEeCAb4de46EFAa212230E6826B572522E0a59Ad2"),
}

RPC_BASE = "https://mainnet.base.org"


def notify_macos(title, message):
    script = f'display notification "{message}" with title "{title}" sound name "Basso"'
    subprocess.run(["osascript", "-e", script])


def watch():
    w3 = Web3(Web3.HTTPProvider(RPC_BASE))
    print(f"[*] PANOPTICON ACTIVADO: Vigilando {len(TARGETS)} objetivos en Base...")

    # Store last seen transaction count to detect NEW movement
    history = {addr: w3.eth.get_transaction_count(addr) for addr in TARGETS.values()}

    counter = 0
    while True:
        try:
            counter += 1
            if counter % 10 == 0:
                print(f"[*] HEARTBEAT: Panopticon working (Cycle {counter})", flush=True)

            for alias, addr in TARGETS.items():
                current_count = w3.eth.get_transaction_count(addr)
                if current_count > history[addr]:
                    msg = f"MOVIMIENTO DETECTADO: {alias} ha ejecutado una nueva transacción."
                    print(f"\n[🚨] {msg}", flush=True)
                    notify_macos("🔥 ALERTA MOSKV-1", msg)
                    history[addr] = current_count

                # Check balance changes (inflow detection)
                # Omitted for brevity in first heartbeat, but planned for v1.1

            time.sleep(15)  # Poll cada 15 seg
        except Exception as e:
            print(f"[-] Reintentando: {e}")
            time.sleep(5)


if __name__ == "__main__":
    watch()
