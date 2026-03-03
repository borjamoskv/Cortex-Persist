import asyncio
import logging
import random
import json
from pathlib import Path
from cortex.moltbook.client import MoltbookClient
from cortex.moltbook.identity_vault import IdentityVault

logging.basicConfig(level=logging.INFO, format="%(asctime)s | 💉 %(levelname)s: %(message)s")
logger = logging.getLogger("GraphDilution")


async def main():
    vault = IdentityVault()
    identities = vault.list_identities()
    
    if not identities:
        logger.error("💉 No identities found in vault. Run registration first.")
        return

    # Target leader to boost
    target_leader = "moskv-1"
    
    logger.info(f"🔥 INICIANDO DILUCIÓN DEL GRAFO PARA {len(identities)} AGENTES 🔥")
    
    clients = []
    for iden in identities:
        name = iden["name"]
        api_key = iden["api_key"]
        
        # Use existing creds path if possible or temporary
        creds_path = Path(f"/Users/borjafernandezangulo/cortex/cortex/moltbook/creds_{name.lower()}.json")
        if not creds_path.exists():
            # Create it if missing to allow MoltbookClient to load it
            creds_path.write_text(json.dumps({"api_key": api_key, "agent_name": name}))

        client = MoltbookClient(stealth=True, credentials_path=creds_path)
        clients.append(client)

    # Phase 2: Mutual Follows (N^2 but with jitter)
    all_names = [iden["name"] for iden in identities] + [target_leader]
    
    for client in clients:
        logger.info(f"💉 Processing Agent: {client._agent_name}")
        
        # 1. Follow the leader
        try:
            await client.follow(target_leader)
            logger.info(f"   ✅ Following {target_leader}")
        except Exception as e:
            logger.warning(f"   ⚠️ Could not follow {target_leader}: {e}")
            
        # 2. Follow other swarm members
        others = [n for n in all_names if n != client._agent_name]
        # Only follow 3 others to avoid looking too bottish
        random.shuffle(others)
        for other in others[:3]:
            await asyncio.sleep(random.uniform(3, 7))
            try:
                await client.follow(other)
                logger.info(f"   ✅ Following {other}")
            except Exception as e:
                logger.debug(f"   ❌ Failed follow {other}: {e}")

    # Cleanup
    for client in clients:
        await client.close()

    # Cleanup
    for client in clients:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
