import os
import re
import codecs
import time
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# ==============================================================================
# 🗡️ PROTOCOLO NÉMESIS: DUST TSUNAMI v2.0 (MULTI-TARGET OVERDRIVE)
# ==============================================================================

# TARGET FLEET (Mapeadas por CORTEX Intel)
TARGETS = {
    "FOIZUR_MASTER": "0x06060c5E3A090A1aFF282BBeC1eB7Db7bdab7a60",
    "ARB_L2_MAIN": "0x7df263b76f67262444952c0bd44f5259e4672642",
    "LINEA_BRIDGE": "0x21EF8825B387C3835E87E1036EB32768D13A212D",
    "NEW_VECTOR": "0x281Bb56E122759f3512a5eE6F3a376c668178962",
    "EIP7702_EXEC": "0xEeCAb4de46EFAa212230E6826B572522E0a59Ad2" # Extrapolated Tier 2
}

RPC_URL = "https://mainnet.base.org"
CHAIN_ID = 8453

# PAYLOADS (Deeper Psychological Warfare)
PAYLOADS = [
    "1. [CORTEX PANOPTICON] SYSTEM DETECTED: FOIZUR (BANGLADESH)",
    "2. IP LOGGED: 103.xxx.xxx.xxx | DEVICE: WINDOWS/CHROME",
    "3. KUCOIN COMPLIANCE ALERT: CASE_ID_9821_MOSKV",
    "4. YOUR L2 MULES ARE TAINTED. EXIT CLOSED.",
    "5. DUST TSUNAMI v2.0: YOUR HISTORY IS CORRUPTED.",
    "6. EVERY SWEEPER YOU RUN IS TRACED BY LEGIØN-1.",
    "7. WE ARE MOSKV-1. ANNIHILATION IS IMMUTABLE."
]

def extract_private_keys(file_path):
    keys = []
    if not os.path.exists(file_path): return keys
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            matches = re.findall(r'(?:0x)?[a-fA-F0-9]{64}', content)
            for m in matches:
                k = m.replace('0x', '').lower()
                if k not in keys: keys.append(k)
    except: pass
    return keys

def get_funder_pk():
    # Prioritizing known funder from previous scans
    target_addr = "0x2340E6826B572522E0a59Ad25f27b600C69820dd"
    env_paths = [
        "/Users/borjafernandezangulo/cortex/.env",
        "/Users/borjafernandezangulo/game/prophecy-nft/.env",
        "/Users/borjafernandezangulo/hardhat-project/.env"
    ]
    for p in env_paths:
        for k in extract_private_keys(p):
            try:
                w3 = Web3()
                if w3.eth.account.from_key(k).address.lower() == target_addr.lower():
                    return k
            except: pass
    return None

def fire_multi_tsunami():
    print("\n" + "!"*80)
    print("🗡️  CORTEX: OPERATION DUST TSUNAMI v2.0 (MULTI-TARGET) 🗡️")
    print("!"*80 + "\n")
    
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    pk = get_funder_pk()
    if not pk:
        print("[-] ERR: Funder Key (0x234...) not found in local vault.")
        return

    sender = w3.eth.account.from_key(pk).address
    bal = w3.eth.get_balance(sender)
    
    # Requirement: ~0.00005 ETH for multi-target volley
    if bal < 5000000000000: # 0.000005 threshold for check
        print(f"[-] GAS LOW: {w3.from_wei(bal, 'ether')} ETH. Need ~0.0005 ETH to fire.")
        return

    print(f"[*] Funder Operative: {sender}")
    base_nonce = w3.eth.get_transaction_count(sender)
    gas_price = int(w3.eth.gas_price * 1.5)
    priority_fee = w3.to_wei(0.005, 'gwei') 
    
    tx_count = 0
    for alias, target_addr in TARGETS.items():
        print(f"\n[!] Targetting {alias} ({target_addr})...")
        for i, p_text in enumerate(PAYLOADS):
            hex_data = "0x" + codecs.encode(p_text.encode("utf-8"), "hex").decode("utf-8")
            
            tx = {
                'nonce': base_nonce + tx_count,
                'to': w3.to_checksum_address(target_addr),
                'value': 0,
                'data': hex_data,
                'gas': 60000, 
                'maxFeePerGas': gas_price,
                'maxPriorityFeePerGas': priority_fee,
                'chainId': CHAIN_ID
            }
            
            try:
                signed_tx = w3.eth.account.sign_transaction(tx, pk)
                tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                print(f"   [+] Volley {i+1}: Payload Delivered -> {tx_hash.hex()}")
                tx_count += 1
                # Small sleep to prevent nonce issues on some RPCs
                time.sleep(0.5)
            except Exception as e:
                print(f"   [-] Batch Failure: {e}")
                break
                
    print("\n✅ MULTI-TARGET TSUNAMI COMPLETED.")
    print("The Syndicate's Basescan footprint is now a monument to their failure.")

if __name__ == "__main__":
    fire_multi_tsunami()
