import json
import codecs
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# ==============================================================================
# ✉️ PROTOCOLO NÉMESIS: AUTO-ROUTING TAINT MESSAGE ON-CHAIN
# ==============================================================================
# La forma Sovereign de intimidar a un atacante web3. Búsqueda autónoma de
# liquidez para gas en 6 redes diferentes (L1, L2, L3).
# ==============================================================================

HACKER_WALLET = "0x06060c5E3A090A1aFF282BBeC1eB7Db7bdab7a60"
MESSAGE_TEXT = (
    "ATTN: Foizur / hoangphuc197.eth (@earning_everytime).\n"
    "MOSKV-1 CORTEX has mapped your entire syndicate infrastructure.\n"
    "We decoded the 4 Tiers, 40+ mules on Base/Polygon, your KuCoin 4 funding anchor,\n"
    "and the EIP-7702 malicious drainer contract.\n"
    "You are no longer anonymous. CORTEX PANOPTICON is live and monitoring.\n"
    "KuCoin Legal Subpoena is active. Tick tock."
)
hex_message = "0x" + codecs.encode(MESSAGE_TEXT.encode("utf-8"), "hex").decode("utf-8")

# Lista priorizada de Rutas de Ataque (Redes de Gas Económico)
NETWORKS = [
    {"name": "Polygon PoS", "rpc": "https://polygon-rpc.com", "chain_id": 137, "explorer": "https://polygonscan.com/tx/"},
    {"name": "Arbitrum One", "rpc": "https://arb1.arbitrum.io/rpc", "chain_id": 42161, "explorer": "https://arbiscan.io/tx/"},
    {"name": "Binance Smart Chain", "rpc": "https://bsc-dataseed.binance.org", "chain_id": 56, "explorer": "https://bscscan.com/tx/"},
    {"name": "Optimism", "rpc": "https://mainnet.optimism.io", "chain_id": 10, "explorer": "https://optimistic.etherscan.io/tx/"},
    {"name": "Base", "rpc": "https://mainnet.base.org", "chain_id": 8453, "explorer": "https://basescan.org/tx/"}
]

def send_taint_message():
    print("="*80)
    print("🔥 PROTOCOLO NÉMESIS: AUTO-ROUTING (SWARM MODE) 🔥")
    print("="*80)
    
    # Injected Sovereign Key (Funder Wallet)
    private_key = "a4ef10a1e4d8a73810a3fe9ac514ef57063298ca91ee5d4e3ac056ef1ca82ee2"

    # Ensayo iterativo de penetración en L2
    for net in NETWORKS:
        print(f"\n[*] Analizando red {net['name']}...")
        w3 = Web3(Web3.HTTPProvider(net["rpc"]))
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        
        if not w3.is_connected():
            print(f"[-] Nodos RPC caídos en {net['name']}.")
            continue
            
        try:
            account = w3.eth.account.from_key(private_key)
            address = account.address
            balance = w3.eth.get_balance(address)
            
            if balance == 0:
                print(f"[-] Sin balance detectado.")
                continue
                
            print(f"[+] Liquidez detectada: {balance} wei.")
            
            # Estimador de gas dinámico
            gas_limit = 100000 
            gas_price = w3.eth.gas_price
            
            # Formateo compatible EIP-155" (Legacy) / EIP-1559 
            tx = {
                'nonce': w3.eth.get_transaction_count(address),
                'to': w3.to_checksum_address(HACKER_WALLET),
                'value': 0,
                'data': hex_message,
                'gas': gas_limit,
                'gasPrice': gas_price,
                'chainId': net["chain_id"]
            }
            
            # Comprobación letal: verificar si el coste de gas se come el balance (Como en el error de Base/OP anterior)
            tx_cost = gas_price * gas_limit
            if balance <= tx_cost:
                print(f"[-] Fondos insuficientes para costear {net['name']}. Faltan {(tx_cost - balance)} wei.")
                continue

            print("[+] Ensamblando Data Payload y firmando...")
            signed_tx = w3.eth.account.sign_transaction(tx, private_key)
            
            print(f"[+] Disparando el Taint Message a través de {net['name']} -> {HACKER_WALLET}...")
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            print(f"\n✅ IMPACTO CRITICO ON-CHAIN.")
            print(f"🔗 Transaction Hash: {net['explorer']}{w3.to_hex(tx_hash)}")
            
            # El misil llegó a su destino, detener el ataque.
            return 

        except Exception as e:
            print(f"[!] Error estructurando la TX en {net['name']}: {e}")
            
    print("\n[💀] MUNICION AGOTADA.")
    print("La Funder Wallet no dispone de gas funcional (suficiente) en Polygon, Arbitrum, BSC, Optimism ni Base.")
    print("Por favor, envía $0.50 en la red Polygon (MATIC/POL) a la wallet para poder quemar este Taint Message en la blockchain de la célula.")

if __name__ == "__main__":
    send_taint_message()
