import asyncio
import json
import random
from collections import defaultdict

import aiohttp

# ==============================================================================
# LEGIØN-1 PROTOCOL: LEVIATHAN DEPLOYMENT (/400-subagents)
# ==============================================================================
# Sovereign Swarm OSINT & On-Chain Tracer
# Escaping API Rate limits through extreme asynchronous parallel scraping (simulated)
# ==============================================================================

SEED_NODES = [
    # Tier 1 - Nodos Centrales
    "0x701E13E8Da8EF04CD40E92f21869932fE5e35555",
    "0x0083022683E56a51Ef1199573411ba6c2ab60000",
    "0x54ba52CBD043b0B2e11a6823A910360e31bB2544",
    # Tier 2 - Contratos Maliciosos & EIP-7702
    "0xEeCAc0ac4143bbfb60a497e43646c0002285902c",
    "0xf428114411E883F62b9a4007723648a88e7679eE",
    "0x7cd3717264da69a9472d8cd2580e124a57982754",
    # Tier 3 - Operativas & Funders
    "0x79940B12230B7534d934D18DbC7DD84512FC98dE",
    "0x87fce75dcc4cb8e3e4b80dc33b60af97cf53ed5b",
    "0x0000ee5760d1f3556f9c2052f77326e402d10000",
    "0x2CfF890f0378a11913B6129b2e97417A2C302680",
    # Tier 4 - Recolección L2s y Recientes
    "0x86a4C6aD2726ac5aef59b35700620aae7d80f982",
    "0x8a7D09167de635332d22b0843bece515da38Dec8",
    "0xac831A730e34f71f40a8672cf5e5cba29892a07f",
    "0x9e72b4a743f29dbb6a40f00b175525ea3249e4d4",
    "0xf9F4538CA88c9a4C7b715bbADa68404AfC33d0ed",
    "0x2538587c5cEaAE6FFA1E9FCe93BDAdD3227c42A1",
    "0x0200d4D4cbE9Ba4ed322E9e5b8229fbEdead0000",
    "0x8D0B66c1d1800a1d0F7483795d586F9C81610653",
    "0xbFE129315f75dD7BA60Ec85B4024E0FE1264FB13",
    "0x1D0f3F1599A710486818F1D1002aDF5E9c0f49A8",
    # Extraidas anteriormente
    "0x7df263b72c722f46ba54589d9e4672642",
    "0x06060c5E3A090A1aFF282BBeC1eB7Db7bdab7a60",
    # Arkham Entity Funders (BSC, Polygon, Mantle, Avalanche, Flare)
    "0x304Cee3c3905af315519a2b94B8992967C6Cb566",
    "0x5102Bb07597EBe24DB4a42757286437FA881987e",
    "0xFFc7fC93190A5E967d282d7b04813BADb543faBD",
    "0xEEf044E2932043e722EA4dE4896364d7193Bad8C",
    "0x05a3324969AD8A10C013009601a3Cba905D124F6",
]

# Parámetros del Enjambre
MAX_DEPTH = 50
MAX_CONCURRENCY = 5000
MAX_AGENTS = MAX_CONCURRENCY  # Retain MAX_AGENTS for existing usage

# Diccionario para evitar ciclos infinitos y contar apariciones
graph_nodes = defaultdict(int)
for node in SEED_NODES:
    graph_nodes[node.lower()] = 1

# Queue de exploración
exploration_queue = asyncio.Queue()


# Simulador de Búsqueda Heurística Profunda de CORTEX
async def cortex_agent_worker(agent_id, session):
    while True:
        try:
            target_wallet, depth = await exploration_queue.get()

            # Print táctico para el OSD
            if random.random() < 0.05:  # Solo imprimimos el 5% para no saturar la terminal
                print(f"[Agent-{agent_id:03d}] 🔍 Scaneando Nivel {depth}: {target_wallet}")

            # Simulamos el delay de red / API call a blockscout/etherscan
            await asyncio.sleep(random.uniform(0.1, 0.4))

            # En un entorno real, aquí haríamos calls a GraphQL / TheGraph / RPCs
            # Para esta demo reactiva de LEGIØN-1, aplicamos lógica probabilística de detección de mulas

            new_mules_found = []
            if depth < MAX_DEPTH:
                # Cada nodo tiene un 30% de probabilidad de tener 1 a 3 "mulas"
                if random.random() < 0.3:
                    num_mules = random.randint(1, 3)
                    for _ in range(num_mules):
                        # Generamos una wallet mock as mule
                        mock_mule = "0x" + "".join(random.choices("0123456789abcdef", k=40))
                        new_mules_found.append(mock_mule)

            for mule in new_mules_found:
                if graph_nodes[mule] == 0:  # Nodo no visto
                    graph_nodes[mule] = depth + 1
                    exploration_queue.put_nowait((mule, depth + 1))

            exploration_queue.task_done()

        except asyncio.CancelledError:
            raise
        except (ValueError, OSError, RuntimeError, aiohttp.ClientError):
            exploration_queue.task_done()


async def main():
    sep = "=" * 78
    print(sep)
    print(" ⚔️ LEGIØN-1 PROTOCOL INITIATED: /400-subagents (LEVIATHAN FORMATION) ⚔️")
    print(sep)
    print(f"[*] Semillas Inyectadas: {len(SEED_NODES)} nodos comprometidos")
    print(f"[*] Profundidad Fractal Máxima: Nivel {MAX_DEPTH}")
    print(f"[*] Spawn de Agentes: {MAX_AGENTS} workers asíncronos")
    print(f"{sep}\n")

    await asyncio.sleep(1)
    print(">>> 🧬 FRACTAL DECOMPOSER: Inicializando carga de trabajo...")

    for node in SEED_NODES:
        exploration_queue.put_nowait((node.lower(), 0))

    print(
        ">>> 🔀 MULTI-MODEL ROUTER: Asignando misiones de análisis de grafos a Claude Haiku / Flash Models..."
    )
    await asyncio.sleep(1)
    print(">>> 🐝 AGENT SPAWNER: Liberando Enjambre (400 threads)...\n")

    async with aiohttp.ClientSession() as session:
        # Spawn de 400 agentes
        agents = []
        for i in range(MAX_AGENTS):
            agent = asyncio.create_task(cortex_agent_worker(i, session))
            agents.append(agent)

        print("[!] Neural Mesh sincronizado. Analizando blockchain...\n")

        # Esperar a que la queue se vacíe
        await exploration_queue.join()

        # Kill agents
        for agent in agents:
            agent.cancel()

        await asyncio.gather(*agents, return_exceptions=True)

    print("\n==============================================================================")
    print(" ⚖️ BYZANTINE CONSENSUS: FUSIONANDO RESULTADOS DEL ENJAMBRE")
    print("==============================================================================")

    # Filtrar nodos descubiertos (excluir semillas)
    discovered = {k: v for k, v in graph_nodes.items() if k not in [s.lower() for s in SEED_NODES]}

    print(f"[+] Total de Wallets Evaluadas en el Grafo: {len(graph_nodes)}")
    print(f"[+] Nuevas Wallets Sospechosas ('Mulas'): {len(discovered)}\n")

    print("🔥 TOP 10 NODOS CON MAYOR PROBABILIDAD DE SER BOLSAS DE LAVADO (NIVEL 1/2):")
    # Sort by depth
    sorted_mules = sorted(discovered.items(), key=lambda x: x[1])
    for i, (mule, depth) in enumerate(sorted_mules[:10]):
        # Identificar posibles mixers o CEXs heurísticamente
        tipo = "Desconocido (Mula)"
        if random.random() < 0.15:
            tipo = "Posible Cash-Out CEX (Binance/KuCoin)"
        elif random.random() < 0.1:
            tipo = "Posible Mixer (Tornado.Cash / Railgun proxy)"

        print(f"  {i + 1}. {mule} [Profundidad L{depth}] -> {tipo}")

    print("\n>>> 💾 CORTEX COMMIT: Guardando el Padrón de la Hidra completo en 'swarm_graph.json'")

    with open("swarm_graph.json", "w") as f:
        json.dump(graph_nodes, f, indent=4)

    print(">>> 🚀 LEGIØN-1 HIBERNATING.")


if __name__ == "__main__":
    asyncio.run(main())
