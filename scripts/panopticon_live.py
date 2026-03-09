import time
import urllib.request
import json
import logging
from datetime import datetime

# ==============================================================================
# 👁️ CORTEX PANOPTICON: SOVEREIGN LIVE RADAR 👁️
# ==============================================================================
# Monitor Activo de Inteligencia de Amenazas.
# Objetivo: Sindicato Foizur (arbithumarb.eth / hoangphuc197.linea.eth)
# ==============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | 🛡️ PANOPTICON | %(message)s',
    datefmt='%H:%M:%S'
)

TARGET_WALLETS = {
    "0x06060c5E3A090A1aFF282BBeC1eB7Db7bdab7a60": "Master Wallet (arbithumarb)",
    "0xFFc77D765Ecd48b48B02008Bbe146bA2A06bcaBD": "Execution / Sweeper",
    "0x21EF8825B387C3835E87E1036EB32768D13A212D": "Identidad Puente (hoangphuc197)"
}

# Usamos endpoints agnósticos y gratuitos
RPC_NODE = "https://ethereum-rpc.publicnode.com"

def get_latest_block():
    req = urllib.request.Request(
        RPC_NODE,
        data=json.dumps({"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "CORTEX-Panopticon/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            return int(json.loads(res.read())["result"], 16)
    except:
        return None

def scan_block(block_number):
    req = urllib.request.Request(
        RPC_NODE,
        data=json.dumps({
            "jsonrpc":"2.0",
            "method":"eth_getBlockByNumber",
            "params":[hex(block_number), True],
            "id":1
        }).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "CORTEX-Panopticon"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read())
            if "result" in data and data["result"]:
                transactions = data["result"].get("transactions", [])
                for tx in transactions:
                    fr = tx.get("from", "").lower()
                    to = tx.get("to", "")
                    to = to.lower() if to else ""
                    
                    if fr in [w.lower() for w in TARGET_WALLETS.keys()]:
                        logging.warning("🚨 ALERTA ROJA: MOVIMIENTO DETECTADO 🚨")
                        logging.warning("Origen: %s -> Destino: %s", TARGET_WALLETS.get(fr, fr), to)
                    elif to in [w.lower() for w in TARGET_WALLETS.keys()]:
                        logging.warning("🚨 ALERTA ROJA: INGRESO DETECTADO 🚨")
                        logging.warning("Origen: %s -> Destino: %s", fr, TARGET_WALLETS.get(to, to))
                return True
    except Exception as e:
        pass
    return False

if __name__ == "__main__":
    print("\n" + "="*70)
    print("👁️  CORTEX PANOPTICON INICIALIZADO 👁️")
    print("Vigilando Activos de la Célula Foizur en Tiempo Real.")
    print("="*70 + "\n")
    
    last_block = get_latest_block()
    if not last_block:
        print("[!] Error fatal conectando al nodo matriz.")
        exit(1)
        
    logging.info("Anclado a la cadena principal. Bloque Actual: %s", last_block)
    logging.info("Modo Sigilo (Silent Polling) Activado...")
    
    # Bucle infinito del Radar PANOPTICON (24/7)
    while True:
        try:
            time.sleep(3)
            current = get_latest_block()
            if current and current > last_block:
                for b_num in range(last_block + 1, current + 1):
                    scan_block(b_num)
                last_block = current
            logging.info("Escaneo rutinario completado. Nodos limpios.")
        except KeyboardInterrupt:
            print("\n[+] Radar PANOPTICON detenido manualmente.")
            break
        except Exception as e:
            logging.error("Error en ciclo de radar: %s", e)
            time.sleep(5)
