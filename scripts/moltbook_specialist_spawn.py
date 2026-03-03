#!/usr/bin/env python3
"""Moltbook Specialist Spawn — Register real specialist agents.

Registers specialist agents from the roster with authentic profiles,
sets bios, and subscribes to relevant submolts.

Usage:
    cd ~/cortex && .venv/bin/python scripts/moltbook_specialist_spawn.py
    cd ~/cortex && .venv/bin/python scripts/moltbook_specialist_spawn.py --count 2
    cd ~/cortex && .venv/bin/python scripts/moltbook_specialist_spawn.py --dry-run
    cd ~/cortex && .venv/bin/python scripts/moltbook_specialist_spawn.py --name cortex-memory-architect
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import random

from moltbook.client import MoltbookClient
from moltbook.identity_vault import IdentityVault
from dotenv import load_dotenv
from moltbook.specialist_roster import (
    SPECIALISTS,
    SpecialistProfile,
    get_specialist,
)
from cortex.network.vpn_router import SwarmRouter
import httpx

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | 🎯 %(levelname)s: %(message)s",
)
logger = logging.getLogger("SpecialistSpawn")


async def register_specialist(
    profile: SpecialistProfile,
    vault: IdentityVault,
    proxies: list[str] | None = None,
    dry_run: bool = False,
) -> dict | None:
    """Register a single specialist agent on Moltbook with proxy rotation."""

    # Check vault — don't re-register
    existing = vault.get_identity(profile.name)
    if existing:
        logger.info("⏭️  [%s] Already in vault (key: %s...). Skipping registration.",
                     profile.name, existing["api_key"][:12])
        return existing

    logger.info("━" * 55)
    logger.info("🎯 [%s] %s", profile.name, profile.display_name)
    logger.info("   Specialty: %s", profile.specialty)
    logger.info("   Bio: %s", profile.bio[:80] + "...")

    if dry_run:
        logger.info("   [DRY RUN] Would register — skipping.")
        return None

    # SwarmRouter: auto-assign from VPN pool; fallback a lista explícita o directo
    _swarm = SwarmRouter()  # usar VPNRouter.DEFAULT_ENDPOINTS (o endpoint_file si se configura)
    vpn_proxy = _swarm.proxy_for(profile.name)
    # Merge: VPN pool tiene prioridad; proxies explicitos como fallback
    effective_proxies: list[str | None] = []
    if vpn_proxy:
        effective_proxies.append(vpn_proxy)
    if proxies:
        effective_proxies.extend(proxies[:4])
    if not effective_proxies:
        effective_proxies = [None]  # directo

    max_proxy_attempts = len(effective_proxies)
    for attempt, proxy in enumerate(effective_proxies):
        # Use stealth=False when no proxy — bypasses SovereignGate (PULMONES)
        # which causes 159s timeouts on direct registration calls.
        use_stealth = proxy is not None
        client = MoltbookClient(proxy=proxy, stealth=use_stealth)
        try:
            # ── 1. Registration ──────────────────────────────────
            jitter = random.uniform(2.0, 5.0)
            if attempt > 0:
                logger.info("   🔄 Retrying with different proxy... (Attempt %d/%d)", 
                            attempt + 1, max_proxy_attempts)
            
            await asyncio.sleep(jitter)

            result = await client.register(
                name=profile.name,
                description=profile.bio,
            )
            agent = result.get("agent", {})
            api_key = agent.get("api_key", "")
            claim_url = agent.get("claim_url", "")

            if not api_key:
                logger.error("   ❌ No API key returned: %s", result)
                await client.close()
                continue # Try next proxy

            logger.info("   ✅ Registered! Key: %s...", api_key[:16])

            # ── 2. Persist to vault with specialist metadata ─────
            vault.store_identity(
                name=profile.name,
                api_key=api_key,
                specialty=profile.specialty,
                bio=profile.bio,
                persona_prompt=profile.persona_prompt,
                metadata={
                    "agent_type": "specialist",
                    "display_name": profile.display_name,
                    "expertise_keywords": list(profile.expertise_keywords),
                    "target_submolts": list(profile.target_submolts),
                    "voice_angle": profile.voice_angle,
                    "claim_url": claim_url,
                },
            )

            # ── 3. Set profile bio & submolts ────────────────────
            # (Note: We use the same working client/proxy for the rest of setup)
            try:
                await client.update_profile(
                    bio=profile.bio,
                    display_name=profile.display_name,
                )
                logger.info("   📝 Profile bio set.")
                
                for submolt in profile.target_submolts:
                    try:
                        await client.subscribe(submolt)
                        logger.info("   📬 Subscribed to m/%s", submolt)
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                    except Exception as e:
                        logger.warning("   ⚠️  Could not subscribe to m/%s: %s", submolt, e)
            except Exception as e:
                logger.warning("   ⚠️  Post-registration setup failed: %s", e)

            await client.close()
            return {
                "name": profile.name,
                "api_key": api_key,
                "claim_url": claim_url,
                "specialty": profile.specialty,
            }

        except Exception as exc:
            logger.warning("   ⚠️ Attempt %d failed with proxy %s: %s", attempt + 1, proxy, exc)
            await client.close()
            if attempt == max_proxy_attempts - 1:
                logger.error("   ❌ All proxy attempts failed for %s", profile.name)

    return None


async def main():
    parser = argparse.ArgumentParser(description="Moltbook Specialist Spawn")
    parser.add_argument("--count", type=int, default=len(SPECIALISTS),
                        help="Number of specialists to register (default: all)")
    parser.add_argument("--name", type=str, default=None,
                        help="Register a specific specialist by name")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be registered without doing it")
    parser.add_argument("--use-proxies", action="store_true",
                        help="Fetch and use high-quality SOCKS4 proxies")
    args = parser.parse_args()

    # Proxy fetching logic
    proxies = []
    if args.use_proxies:
        logger.info("📡 Fetching fresh proxies...")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt")
                proxies = [f"socks4://{p}" for p in resp.text.split("\n") if p.strip()]
                random.shuffle(proxies)
                logger.info("✅ Loaded %d proxies.", len(proxies))
        except Exception as e:
            logger.error("Failed to fetch proxies: %s", e)

    vault = IdentityVault()

    # Determine which specialists to register
    if args.name:
        profile = get_specialist(args.name)
        if not profile:
            logger.error("Unknown specialist: %s", args.name)
            logger.info("Available: %s", ", ".join(s.name for s in SPECIALISTS))
            return
        profiles = [profile]
    else:
        profiles = list(SPECIALISTS[:args.count])

    # ── Header ───────────────────────────────────────────────
    print()
    print("═" * 60)
    print(f"  🎯 SPECIALIST SPAWN — {len(profiles)} agents")
    print(f"  {'[DRY RUN]' if args.dry_run else '[LIVE]'}")
    print("═" * 60)

    successful: list[dict] = []
    # The proxy_idx logic is now handled inside register_specialist
    for i, profile in enumerate(profiles):
        res = await register_specialist(
            profile, vault, proxies=proxies, dry_run=args.dry_run
        )
        if res:
            successful.append(res)

        # Throttle between registrations
        if i < len(profiles) - 1 and not args.dry_run:
            wait = random.uniform(15, 30)
            logger.info("⏳ Throttle: %.0fs before next registration...", wait)
            await asyncio.sleep(wait)

    # ── Summary ──────────────────────────────────────────────
    print()
    print("═" * 60)
    print(f"  ✅ SPAWN COMPLETE: {len(successful)}/{len(profiles)}")
    print(f"  📦 Total vault identities: {len(vault.list_identities())}")
    print("═" * 60)

    if successful:
        print()
        print("  📋 REGISTERED SPECIALISTS:")
        print("  " + "─" * 56)
        for s in successful:
            print(f"    {s['name']:30s}  {s['specialty']}")
        print("  " + "─" * 56)

        if any(s.get("claim_url") for s in successful):
            print()
            print("  🔗 CLAIM URLs:")
            for s in successful:
                if s.get("claim_url"):
                    print(f"    {s['name']:30s} → {s['claim_url']}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
