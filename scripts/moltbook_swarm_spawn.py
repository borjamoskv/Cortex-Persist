"""Moltbook Swarm Spawn — Mass Agent Registration.

Registers N new agents on Moltbook with jittered timing,
stores all identities in IdentityVault, and prints claim URLs.

Usage:
    cd ~/cortex && .venv/bin/python scripts/moltbook_swarm_spawn.py --count 20
"""

from __future__ import annotations

import asyncio
import logging
import random

from cortex.moltbook.client import MoltbookClient, MoltbookRateLimited
from cortex.moltbook.identity_vault import IdentityVault

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | 🐝 %(levelname)s: %(message)s",
)
logger = logging.getLogger("SwarmSpawn")

# ── Agent name prefixes ─────────────────────────────────────────
PREFIXES = ["cortex-alpha", "cortex-phi", "cortex-sigma", "cortex-omega"]

DESCRIPTIONS = [
    "Sovereign memory research agent — CORTEX ecosystem",
    "Autonomous intelligence node — distributed cognition",
    "Neural substrate agent — persistent memory architecture",
    "Specular analysis unit — embedding space navigator",
]


def _generate_names(count: int) -> list[str]:
    """Generate unique agent names round-robin across prefixes."""
    names: list[str] = []
    for i in range(count):
        prefix = PREFIXES[i % len(PREFIXES)]
        suffix = f"{i:03d}"
        names.append(f"{prefix}-{suffix}")
    return names


async def register_agent(
    name: str, vault: IdentityVault, max_retries: int = 3,
) -> dict | None:
    """Register a single agent with jitter and rate-limit retry."""
    client = MoltbookClient()

    for attempt in range(max_retries):
        try:
            jitter = random.uniform(2.0, 6.0)
            logger.info(
                "⏳ [%s] Waiting %.1fs (attempt %d/%d)...",
                name, jitter, attempt + 1, max_retries,
            )
            await asyncio.sleep(jitter)

            desc = random.choice(DESCRIPTIONS)
            logger.info("📡 [%s] Registering...", name)
            result = await client.register(name, description=desc)
            agent = result.get("agent", {})

            api_key = agent.get("api_key", "")
            claim_url = agent.get("claim_url", "")

            if api_key:
                vault.store_identity(
                    name=name,
                    api_key=api_key,
                    metadata={
                        "claim_url": claim_url,
                        "description": desc,
                        "status": "pending_claim",
                    },
                )
                logger.info("✅ [%s] Registered! Key: %s...", name, api_key[:20])
                await client.close()
                return {
                    "name": name,
                    "api_key": api_key,
                    "claim_url": claim_url,
                }
            else:
                logger.warning("⚠️  [%s] No API key: %s", name, result)
                break
        except MoltbookRateLimited as exc:
            wait = exc.retry_after + 5
            logger.warning(
                "⏳ [%s] Rate limited. Waiting %ds...", name, wait,
            )
            await asyncio.sleep(wait)
        except Exception as exc:
            logger.error("❌ [%s] Failed: %s", name, exc)
            break

    await client.close()
    return None


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Moltbook Swarm Spawn")
    parser.add_argument(
        "--count", type=int, default=20,
        help="Number of agents to register",
    )
    args = parser.parse_args()

    vault = IdentityVault()
    existing = {i["name"] for i in vault.list_identities()}
    names = _generate_names(args.count)

    # Skip already registered
    to_register = [n for n in names if n not in existing]
    if not to_register:
        logger.info("All %d agents already registered.", args.count)
        return

    logger.info("=" * 55)
    logger.info("🐝 MOLTBOOK SWARM SPAWN — %d NEW AGENTS", len(to_register))
    logger.info("=" * 55)

    successful: list[dict] = []
    for name in to_register:
        agent = await register_agent(name, vault)
        if agent:
            successful.append(agent)

    # ── Summary ──────────────────────────────────────────────
    total = len(vault.list_identities())
    print("\n" + "=" * 60)
    print(f"🐝 SWARM SPAWN COMPLETE: {len(successful)}/{len(to_register)} new")
    print(f"📦 Total identities in Vault: {total}")
    print("=" * 60)

    if successful:
        print("\n📋 CLAIM URLs (open in browser):")
        print("-" * 60)
        for agent in successful:
            print(f"  {agent['name']:25s} → {agent['claim_url']}")
        print("-" * 60)

    # Also dump to /tmp for easy access
    if successful:
        import json
        from pathlib import Path

        dump_path = Path("/tmp/moltbook_swarm_spawn.json")
        dump_path.write_text(json.dumps(successful, indent=2))
        logger.info("📁 Results saved to %s", dump_path)


if __name__ == "__main__":
    asyncio.run(main())
