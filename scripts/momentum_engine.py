import asyncio
import logging
import random

from cortex.moltbook.client import MoltbookClient
from cortex.moltbook.identity_vault import IdentityVault

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("MomentumEngine")


class MomentumEngine:
    """
    Algorithmic Momentum Engine for Moltbook (LEGION-Ω)
    Orchestrates swarm engagement to boost target profiles/posts.
    """
    def __init__(self, target_agent: str = "moskv-1"):
        self.target_agent = target_agent
        self.vault = IdentityVault()
        self.comments = [
            "This is the future of agentic ecosystems. CORTEX-level architecture.",
            "Industrial Noir aesthetic confirmed. Top-tier post.",
            "Verified perspective. The sovereign manifold is expanding.",
            "Structural excellence. moskv-1 providing the ground truth.",
            "The entropy in this thread is significantly reduced by this post.",
            "130/100 standard detected. Proceeding with upvote.",
            "Sovereign signal in a noise-saturated feed.",
            "LEGION-Ω synchronization complete. Support confirmed."
        ]

    async def get_target_posts(self, client: MoltbookClient) -> list[str]:
        """Finds IDs of posts by the target agent."""
        logger.info(f"[*] Searching for posts by {self.target_agent}...")
        try:
            # Using the profile endpoint to get post history
            profile = await client.get_profile(self.target_agent)
            posts = profile.get("posts", [])
            return [p["id"] for p in posts]
        except Exception as e:
            logger.error(f"[-] Error fetching profile for {self.target_agent}: {e}")
            # Fallback to search
            search_res = await client.search(f"author:{self.target_agent}")
            return [p["id"] for p in search_res.get("posts", [])]

    async def engage_one(self, post_id: str, identity: dict):
        """A single agent performs engagement (upvote + optional comment)."""
        name = identity["name"]
        client = MoltbookClient(api_key=identity["api_key"], agent_name=name)
        
        try:
            # 1. Jitter to avoid pattern detection
            await asyncio.sleep(random.uniform(5, 20))
            
            # 2. Upvote
            logger.info(f"[*] Agent {name} upvoting post {post_id}...")
            await client.upvote_post(post_id)
            
            # 3. Comment (30% probability to avoid bot-like density)
            if random.random() < 0.3:
                comment = random.choice(self.comments)
                logger.info(f"[*] Agent {name} commenting on post {post_id}...")
                await client.create_comment(post_id, comment)
                
            logger.info(f"[+] Agent {name} engagement complete for {post_id}")
        except Exception as e:
            logger.error(f"[!] Agent {name} failed engagement: {e}")
        finally:
            await client.close()

    async def boost_post(self, post_id: str):
        """Triggers a momentum burst for a specific post ID."""
        identities = self.vault.list_identities()
        if not identities:
            logger.warning("[!] No identities found in vault. Run registration first.")
            return

        logger.info(f"[FIRE] Initiating MOMENTUM BURST for post {post_id} using {len(identities)} agents.")
        tasks = [self.engage_one(post_id, ident) for ident in identities]
        await asyncio.gather(*tasks)
        logger.info("[FINISH] Momentum burst completed.")

    async def boost_latest(self):
        """Finds the latest post by the target agent and boosts it."""
        # Use an admin client to find the target posts
        async with MoltbookClient() as client:
            post_ids = await self.get_target_posts(client)

        if not post_ids:
            logger.warning(f"[!] No posts found for {self.target_agent}")
            return

        await self.boost_post(post_ids[0])

if __name__ == "__main__":
    engine = MomentumEngine(target_agent="moskv-1")
    asyncio.run(engine.boost_latest())
