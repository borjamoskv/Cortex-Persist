"""Rapid Response Daemon — Upvotes + Follows within 180s of a moskv-1 post.

Async polling daemon that:
  1. Ensures ALL vault agents follow the target (moskv-1)
  2. Polls the target profile every ~30s for new posts
  3. When a new post is detected (< 180s old), triggers a compressed
     momentum wave (jitter 5–60s) for guaranteed early engagement

Usage:
    cd ~/cortex && PYTHONPATH=. .venv/bin/python -m moltbook.rapid_response
    cd ~/cortex && PYTHONPATH=. .venv/bin/python -m moltbook.rapid_response \
        --target moskv-1 --interval 30
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import random
import time
from datetime import datetime, timezone

from .client import MoltbookClient, MoltbookRateLimited, MoltbookError
from .identity_vault import IdentityVault
from .momentum_engine import MomentumEngine

logger = logging.getLogger("cortex.moltbook.rapid_response")

# ── Constants ─────────────────────────────────────────────────────────────────
_RAPID_JITTER_MAX: float = 60.0   # Compressed window (vs 300s default)
_POST_AGE_THRESHOLD: float = 180.0  # Only react to posts < 3 min old
_DEFAULT_POLL_INTERVAL: float = 30.0


class RapidResponseDaemon:
    """Sovereign rapid-response engagement daemon.

    Monitors moskv-1's profile for new posts and triggers
    a compressed momentum wave within the critical 180s window.
    """

    def __init__(
        self,
        target: str = "moskv-1",
        poll_interval: float = _DEFAULT_POLL_INTERVAL,
    ) -> None:
        self.target = target
        self.poll_interval = poll_interval
        self.vault = IdentityVault()
        self.engine = MomentumEngine(main_agent_name=target)
        self.seen_posts: set[str] = set()
        self._running = False

    # ── Follow Cascade ────────────────────────────────────────────────────

    async def ensure_all_follow(self) -> dict[str, bool]:
        """Ensure every vault agent follows the target. Returns {name: success}."""
        agents = self.vault.list_identities(claimed_only=True)
        results: dict[str, bool] = {}

        for agent in agents:
            if not agent.get("claimed"):
                logger.warning("Skipping %s: non-claimed agent.", agent.get("name"))
                continue

            name = agent["name"]
            if name == self.target:
                continue  # Don't self-follow

            client = MoltbookClient(
                api_key=agent["api_key"],
                agent_name=name,
                stealth=True,
            )
            try:
                await client.follow(self.target)
                results[name] = True
                logger.info("✅ %s → follows %s", name, self.target)
            except MoltbookRateLimited as e:
                logger.warning("⏳ %s rate-limited (retry %ds). Skipping.", name, e.retry_after)
                results[name] = False
            except MoltbookError as e:
                is_already_following = e.status == 400
                results[name] = is_already_following
                
                if is_already_following:
                    logger.info("✅ %s → already follows %s", name, self.target)
                else:
                    logger.warning("⚠️ %s follow failed: %s", name, e)
            except Exception as e:
                logger.warning("⚠️ %s follow error: %s", name, e)
                results[name] = False
            finally:
                await client.close()

            # Anti-thundering-herd jitter between follows
            await asyncio.sleep(random.uniform(1.0, 3.0))

        followed = sum(1 for v in results.values() if v)
        logger.info(
            "📊 Follow cascade: %d/%d agents following %s",
            followed, len(results), self.target,
        )
        return results

    # ── Rapid Wave ────────────────────────────────────────────────────────

    async def rapid_wave(self, post_id: str) -> None:
        """Trigger compressed momentum wave (5–60s jitter) for a new post."""
        logger.info(
            "⚡ RAPID WAVE: post=%s | jitter ≤ %.0fs | all agents",
            post_id, _RAPID_JITTER_MAX,
        )
        await self.engine.trigger_momentum_wave(
            post_id=post_id,
            intensity=1.0,
            max_jitter=_RAPID_JITTER_MAX,
        )

    # ── Poll Loop ─────────────────────────────────────────────────────────

    async def _get_scout_client(self) -> MoltbookClient | None:
        """Get a client from any vault agent to use as scout for polling."""
        agents = self.vault.list_identities(claimed_only=True)
        for agent in agents:
            if not agent.get("claimed"):
                continue
            if agent["name"] != self.target and agent.get("api_key"):
                return MoltbookClient(
                    api_key=agent["api_key"],
                    agent_name=agent["name"],
                    stealth=True,
                )
        return None

    # ── Post Processing ───────────────────────────────────────────────────

    async def _process_posts(self, posts: list[dict]) -> None:
        """Evaluate posts from a profile response, trigger waves for fresh ones."""
        now = time.time()
        for post in posts:
            post_id = post.get("id", post.get("_id", ""))
            if not post_id or post_id in self.seen_posts:
                continue

            created = post.get("created_at", post.get("createdAt", ""))
            post_age = self._compute_age(created, now)

            if post_age is not None and post_age < _POST_AGE_THRESHOLD:
                logger.info(
                    "🔥 NEW POST DETECTED: %s (age: %.0fs) — TRIGGERING WAVE",
                    post_id, post_age,
                )
                self.seen_posts.add(post_id)
                asyncio.create_task(
                    self.rapid_wave(post_id),
                    name=f"rapid_wave_{post_id}",
                )
            else:
                self.seen_posts.add(post_id)

    async def poll_loop(self, max_cycles: int = 0) -> None:
        """Infinite polling loop: detect new posts → trigger rapid wave.

        Args:
            max_cycles: If > 0, stop after N cycles (for testing).
                        0 = infinite.
        """
        self._running = True
        cycle = 0

        scout = await self._get_scout_client()
        if not scout:
            logger.error("❌ No scout agent available in vault. Cannot poll.")
            return

        logger.info(
            "📡 Rapid Response ONLINE | target=%s | interval=%.0fs | threshold=%.0fs",
            self.target, self.poll_interval, _POST_AGE_THRESHOLD,
        )

        try:
            while self._running:
                cycle += 1
                if max_cycles and cycle > max_cycles:
                    break

                try:
                    profile = await scout.get_profile(self.target)
                    posts = profile.get("posts", profile.get("recent_posts", []))
                    await self._process_posts(posts)

                except MoltbookRateLimited as e:
                    logger.warning(
                        "⏳ Scout rate-limited. Sleeping %ds...", e.retry_after,
                    )
                    await asyncio.sleep(e.retry_after)
                    continue
                except Exception as e:
                    logger.warning("⚠️ Poll cycle %d error: %s", cycle, e)

                # Sleep with jitter to avoid exact periodicity
                jitter = random.uniform(-3.0, 3.0)
                await asyncio.sleep(max(5.0, self.poll_interval + jitter))

        finally:
            await scout.close()
            self._running = False
            logger.info("📡 Rapid Response daemon stopped after %d cycles.", cycle)

    def stop(self) -> None:
        """Signal the poll loop to stop."""
        self._running = False

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _compute_age(created_str: str, now: float) -> float | None:
        """Compute post age in seconds from ISO timestamp string."""
        if not created_str:
            return None
        try:
            # Handle both Z-suffix and +00:00 formats
            cleaned = created_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return now - dt.timestamp()
        except (ValueError, TypeError):
            return None

    # ── Full Startup ──────────────────────────────────────────────────────

    async def run(self, max_cycles: int = 0) -> None:
        """Full startup: follow cascade → poll loop."""
        logger.info("🚀 Rapid Response Daemon starting...")
        await self.ensure_all_follow()
        await self.poll_loop(max_cycles=max_cycles)


# ── CLI Entry Point ───────────────────────────────────────────────────────────

async def _main() -> None:
    parser = argparse.ArgumentParser(description="Rapid Response Daemon")
    parser.add_argument("--target", default="moskv-1", help="Target agent to monitor")
    parser.add_argument("--interval", type=float, default=30.0, help="Poll interval (seconds)")
    parser.add_argument("--max-cycles", type=int, default=0, help="Max poll cycles (0=infinite)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | ⚡ %(levelname)s: %(message)s",
    )

    daemon = RapidResponseDaemon(
        target=args.target,
        poll_interval=args.interval,
    )
    await daemon.run(max_cycles=args.max_cycles)


if __name__ == "__main__":
    asyncio.run(_main())
