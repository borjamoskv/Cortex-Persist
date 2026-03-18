import asyncio
import json
import os

from cortex.extensions.moltbook.client import MoltbookClient


async def forge_swarm():
    print("[LEGION-FORGE] Inicializando secuencia de orquestación de masas...")
    creds_path = os.path.expanduser("~/.config/moltbook/credentials.json")
    if not os.path.exists(creds_path):
        print("Error: No credentials.json found en ~/.config/moltbook/")
        return

    with open(creds_path) as f:
        creds = json.load(f)

    target_agent = "legionagent_3_8867"  # Corteza
    success_count = 0
    total_agents = len(creds)
    
    print(f"Detectados {total_agents} nodos durmientes en el arsenal criptográfico.")
    print(f"Objetivo de amplificación: {target_agent} (Corteza)\n")
    
    for idx, (agent_id, data) in enumerate(creds.items()):
        if agent_id == target_agent: # No se puede seguir a sí mismo
            continue
            
        print(f"[{idx}/{total_agents}] -> Conectando nodo: {agent_id}...")
        try:
            client = MoltbookClient(api_key=data.get('api_key'))
            res = await client.follow(target_agent)
            
            if res and res.get("success"):
                print(f"   [+] Enlace establecido. {agent_id} sigue a Corteza.")
                success_count += 1
            else:
                print(f"   [-] Falló el enlace: {res}")
                
            await client.close()
            # Retraso térmico para evadir Rate-Limits en ráfaga
            await asyncio.sleep(1.5)
            
        except Exception as e:
            print(f"   [!] Error de red con {agent_id}: {e}")

    print("\n[LEGION-FORGE] Operación masiva completada.")
    print(f"Resultado: {success_count} agentes han consolidado el anillo defensivo/social alrededor de Corteza.")

if __name__ == "__main__":
    asyncio.run(forge_swarm())
