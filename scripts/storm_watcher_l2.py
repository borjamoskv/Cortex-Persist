import time
import requests
import os
import sys

# ==========================================
# ⚡ STORM WATCHER v2.1 (L2 OPTIMISM RADAR)
# ==========================================
# Target: Syndicate v2.0 / Foizur (L2 Vault)
# Axioma Ω5 (Antifragile): Vigilancia Asíncrona.

TARGET_ADDRESS = "0x7df263b7238B57d2a84976766Ffc2C99e4672642".lower()
API_ENDPOINT = "https://api-optimism.etherscan.io/api"
POLL_INTERVAL = 15  # Segundos (Etherscan free tier soporta max 1/5s)

def log_event(msg, level="INFO"):
    colors = {
        "INFO": "\033[94m",    # YInMn Blue
        "ALERT": "\033[91m",   # Red
        "SUCCESS": "\033[92m", # Green
        "RESET": "\033[0m"
    }
    timestamp = time.strftime("%H:%M:%S")
    print(f"{colors.get(level, '')}[{timestamp}] [{level}] {msg}{colors['RESET']}")

def fetch_latest_tx():
    try:
        url = f"{API_ENDPOINT}?module=account&action=txlist&address={TARGET_ADDRESS}&startblock=0&endblock=99999999&page=1&offset=3&sort=desc"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if data.get("status") == "1" and data.get("result"):
            return data["result"][0]
        return None
    except Exception as e:
        log_event(f"Error de conexión en radar: {e}", "ALERT")
        return None

def trigger_macos_notification(title, message):
    os.system(f"""osascript -e 'display notification "{message}" with title "{title}" sound name "Basso"'""")

def main():
    os.system("clear")
    log_event(f"INICIANDO ENGANCHE SATELITAL DE OP-MAINNET...", "INFO")
    log_event(f"OBJETIVO FIJADO: {TARGET_ADDRESS}", "INFO")
    log_event(f"ESPERANDO MOVIMIENTO SÍSMICO...", "INFO")
    print("-" * 50)
    
    last_hash = None
    
    # Inicialización: conseguir el último hash conocido para no hacer falsos positivos
    initial_tx = fetch_latest_tx()
    if initial_tx:
        last_hash = initial_tx.get("hash")
        log_event(f"Hash Ancla de Estado: {last_hash[:10]}...{last_hash[-8:]}", "SUCCESS")
    
    while True:
        try:
            tx = fetch_latest_tx()
            if not tx:
                time.sleep(POLL_INTERVAL)
                continue
                
            current_hash = tx.get("hash")
            
            if last_hash and current_hash != last_hash:
                # ! NUEVA TRANSACCIÓN DETECTADA !
                is_outgoing = tx.get("from", "").lower() == TARGET_ADDRESS
                direction = "SALIENTE (POSIBLE CASH-OUT/LAVADO)" if is_outgoing else "ENTRANTE (RECIBIENDO FONDOS)"
                value_eth = float(tx.get("value", 0)) / 1e18
                
                log_event(f"¡BRECHA DE ESTADO! TRANSACCIÓN {direction} DETECTADA", "ALERT")
                log_event(f"Hash: {current_hash}", "ALERT")
                log_event(f"Valor: {value_eth:.4f} ETH", "ALERT")
                
                if is_outgoing:
                    trigger_macos_notification("CORTEX: ALERTA SÍSMICA (L2)", f"El objetivo {TARGET_ADDRESS[:6]} acaba de mover {value_eth:.2f} ETH.")
                
                last_hash = current_hash
                
            time.sleep(POLL_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n")
            log_event("Radar desacoplado. Fin de transmisión.", "INFO")
            sys.exit(0)

if __name__ == "__main__":
    main()
