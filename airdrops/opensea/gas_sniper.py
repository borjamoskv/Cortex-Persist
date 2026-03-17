import asyncio
import aiohttp
import sys
from decimal import Decimal
from datetime import datetime
import json

class OpenSeaGasSniper:
    """
    moneytv-1 Gas Sniper. 
    Monitorea el gas de Ethereum de forma asíncrona para encontrar el valle óptimo
    y evitar el gas war inicial del airdrop.
    """
    
    def __init__(self, target_gwei: Decimal):
        self.rpc_url = "https://cloudflare-eth.com"
        self.target_gwei = target_gwei
        self.is_running = True

    async def fetch_gas(self, session: aiohttp.ClientSession) -> Decimal:
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_gasPrice",
            "params": [],
            "id": 1
        }
        try:
            async with session.post(self.rpc_url, json=payload, timeout=5) as response:
                response.raise_for_status()
                data = await response.json()
                wei = int(data["result"], 16)
                # Convertir Wei a Gwei
                gwei = Decimal(wei) / Decimal(10**9)
                return gwei
        except (aiohttp.ClientError, json.JSONDecodeError, KeyError) as e:
            # Zero-Trust exception handling
            print(f"[!] Error de red o parseo en la RPC: {e}")
            return Decimal("-1")

    async def start(self):
        print(f"\n[⚡] MOSKV-1 GAS SNIPER INICIADO")
        print(f"[🎯] TARGET GWEI: {self.target_gwei} o menor\n")
        
        async with aiohttp.ClientSession() as session:
            while self.is_running:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                gwei = await self.fetch_gas(session)
                
                if gwei == Decimal("-1"):
                    await asyncio.sleep(5)
                    continue

                if gwei <= self.target_gwei:
                    print(f"[{now}] 🟢 GWEI ÓPTIMO: {gwei:.2f} Gwei. ¡VENTANA DE CLAIM ABIERTA!")
                    # Podríamos disparar un sonido en macOS
                    sys.stdout.write('\a')
                    sys.stdout.flush()
                else:
                    print(f"[{now}] 🔴 GWEI ALTO: {gwei:.2f} Gwei (Target: {self.target_gwei}). Esperando valle...")
                
                await asyncio.sleep(10)

if __name__ == "__main__":
    # Gwei objetivo por defecto. Modificar según convenga.
    target_gwei_input = Decimal("40.0") 
    if len(sys.argv) > 1:
        try:
            target_gwei_input = Decimal(sys.argv[1])
        except ValueError:
            print("[!] Argumento inválido. Usando 40.0 Gwei.")
            
    sniper = OpenSeaGasSniper(target_gwei_input)
    try:
        asyncio.run(sniper.start())
    except KeyboardInterrupt:
        print("\n[!] Sniper terminado por el operador.")
