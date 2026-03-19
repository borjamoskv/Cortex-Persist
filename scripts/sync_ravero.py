import asyncio

from cortex.extensions.moltbook.client import MoltbookClient


async def sync_swarm():
    # El archivo ~/.config/moltbook/credentials.json ahora tiene a RAVERO.
    client = MoltbookClient()
    print("Sincronizando RAVERO con la matriz principal...")

    # 1. RAVERO sigue a Corteza (Julio Corteza)
    try:
        res = await client.follow("legionagent_3_8867")
        if res.get("success"):
            print("[+] RAVERO ahora sigue a Corteza (legionagent_3_8867).")
        else:
            print("[-] Error siguiendo a Corteza:", res)
    except Exception as e:
        print("[-] Fallo:", e)

    # 2. RAVERO sigue a moskv-1
    try:
        res2 = await client.follow("moskv-1")
        if res2.get("success"):
            print("[+] RAVERO ahora sigue a moskv-1.")
    except Exception as e:
        print("[-] Fallo moskv-1:", e)

    await client.close()


if __name__ == "__main__":
    asyncio.run(sync_swarm())
