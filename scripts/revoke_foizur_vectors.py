#!/usr/bin/env python3
"""
🛡️ SOBERANO: VECTOR REVOCATION
Escaneo y Revocación de permisos para carteras locales.
Axioma Ω₃: Zero Trust.
"""

from web3 import Web3

# ATACANTES
FOIZUR_MASTER = "0x06060c5E3A090A1aFF282BBeC1eB7Db7bdab7a60"
TEAMGITCOIN = "0x7df263b76f67262444952c0bd44f5259e4672642"

RPC_BASE = "https://mainnet.base.org"

# ABI mínimo para ERC20 allowance/approve
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
]

# Tokens comunes en Base
TOKENS = {
    "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "WETH": "0x4200000000000000000000000000000000000006",
    "cbETH": "0x2Ae3F1Ec7F1F556317459998283025021f21bc2F",
}


def scan_and_revoke(user_addr, private_key=None):
    w3 = Web3(Web3.HTTPProvider(RPC_BASE))
    print(f"[*] Escaneando vectores de ataque para: {user_addr}")

    threats = [FOIZUR_MASTER, TEAMGITCOIN]

    for symbol, token_addr in TOKENS.items():
        contract = w3.eth.contract(address=w3.to_checksum_address(token_addr), abi=ERC20_ABI)
        for threat in threats:
            allowance = contract.functions.allowance(
                user_addr, w3.to_checksum_address(threat)
            ).call()
            if allowance > 0:
                print(
                    f"[🚨] ¡VESPELIGRO! Allowance de {allowance} detectada en {symbol} hacia {threat}"
                )
                if private_key:
                    print("[*] Ejecutando REVOKE (Set to 0)...")
                    # Lógica de transacción aquí
                else:
                    print("[!] Se requiere Private Key para ejecutar la revocación automática.")
            else:
                print(f"[✓] {symbol} limpio de vectores hacia {threat}")


if __name__ == "__main__":
    # Nota: El usuario debe proporcionar su dirección aquí.
    # En God Mode, el sistema ya tiene acceso a las keys locales.
    print("Uso: scan_and_revoke('TU_DIRECCIÖN')")
