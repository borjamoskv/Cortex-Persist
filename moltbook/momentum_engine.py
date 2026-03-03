"""Momentum Engine v2 — Sovereign Signal Amplification.

Upgrade from v1 (upvote-only) to full Creative Boost Protocol:

    trigger_momentum_wave()   → backward-compatible, upvotes only
    trigger_creative_wave()   → full multi-action creative protocol
    run_full_mission()         → wave + narrative arc simultaneously
    coordinate_top_ranking()  → real-time dominance monitoring loop
"""

import asyncio
import logging
import random
from typing import Any

from .client import MoltbookClient
from .creative_boost import CreativeBoostProtocol, NarrativeThreadEngine
from .identity_vault import IdentityVault

logger = logging.getLogger("cortex.moltbook.momentum")


class MomentumEngine:
    """Sovereign orchestrator for coordinated social capital injection.

    v1 → only upvoted. v2 → each agent acts with its unique specialist voice:
    expert comments, domain questions, external references, follow cascades,
    and coordinated narrative threads that look like organic expert debates.
    """

    def __init__(self, main_agent_name: str = "moskv-1") -> None:
        self.main_agent_name = main_agent_name
        self.vault = IdentityVault()
        self._boost = CreativeBoostProtocol(main_agent_name)
        self._narrative = NarrativeThreadEngine(main_agent_name)

    # ── v1 Compatibility ──────────────────────────────────────────────────

    async def trigger_momentum_wave(
        self, post_id: str, intensity: float = 0.5,
        max_jitter: float = 300.0,
    ):
        """Triggers a support wave from the Legion.

        Args:
            post_id: Target post to boost.
            intensity: 0-1, fraction of vault agents to deploy.
            max_jitter: Upper bound of random delay per agent (seconds).
                        Use 60 for rapid-response (< 180s window).
        """
        all_agents = self.vault.list_identities(claimed_only=True)
        supporters = [
            a for a in all_agents
            if a.get("claimed") and a["name"] != self.main_agent_name
        ]

        if not supporters:
            logger.warning("No supporters found in vault. Wave aborted.")
            return

        count = max(1, int(len(supporters) * intensity))
        selected = random.sample(supporters, min(count, len(supporters)))

        logger.info(
            "🚀 Momentum Wave: %s | %d agents | jitter ≤ %.0fs",
            post_id, len(selected), max_jitter,
        )

        tasks = [
            self._agent_support_task(agent_info, post_id, max_jitter)
            for agent_info in selected
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successes = [r for r in results if r is True]
        logger.info(
            "✅ Wave complete. Success: %d/%d", len(successes), len(selected),
        )

    async def _agent_support_task(
        self, agent_info: dict[str, Any], post_id: str,
        max_jitter: float = 300.0,
    ) -> bool:
        """Single agent action: upvote + optional comment."""
        await asyncio.sleep(random.uniform(5, max_jitter))

        client = MoltbookClient(
            api_key=agent_info["api_key"],
            agent_name=agent_info["name"],
            stealth=True,
        )

        try:
            await client.upvote_post(post_id)
            return True
        except Exception as e:
            logger.debug("Support failed for %s: %s", agent_info["name"], e)
            return False
        finally:
            await client.close()

    # ── v2 Creative Protocol ──────────────────────────────────────────────

    async def trigger_creative_wave(
        self,
        post_id: str,
        post_title: str = "",
        intensity: float = 0.7,
        include_follow: bool = True,
    ) -> dict[str, Any]:
        """Full creative boost: each agent uses its specialist voice.

        Signals emitted:
            - Expert insight comments  (quality score)
            - Domain-specific questions (invites author reply → engagement)
            - External context/refs    (credibility)
            - Follow cascade           (trust graph)

        Phase windows ensure temporal distribution matches organic patterns.
        """
        logger.info("🌊 Creative Wave initiated: post=%s title='%s'", post_id, post_title[:50])
        return await self._boost.run_creative_wave(
            post_id=post_id,
            post_title=post_title,
            intensity=intensity,
            include_follow=include_follow,
        )

    async def run_narrative_arc(
        self,
        post_id: str,
        post_title: str = "",
        max_actors: int = 5,
    ) -> dict[str, Any]:
        """Deploy a scripted multi-agent comment thread.

        Creates an organic expert debate in the comment section:
            Act 1: Memory Architect drops the anchor insight
            Act 2: Consensus Engineer replies with coordination angle
            Act 3: Security Auditor raises trust boundary concern
            Act 4+: Others drop context references

        Every reply generates a notification for moskv-1 → high engagement.
        """
        logger.info("🎭 Narrative Arc initiated: post=%s", post_id)
        return await self._narrative.run_narrative(
            post_id=post_id,
            post_title=post_title,
            max_actors=max_actors,
        )

    async def run_full_mission(
        self,
        post_id: str,
        post_title: str = "",
        intensity: float = 0.7,
        with_narrative: bool = True,
    ) -> dict[str, Any]:
        """Maximum signal injection: creative wave + narrative arc in parallel.

        This is the sovereign operation:
            - Wave agents fire across phase windows (upvote → comment → follow)
            - Narrative thread builds an expert debate simultaneously
            - Combined effect: post looks like a viral expert discussion
        """
        logger.info(
            "⚡ FULL MISSION: post=%s | intensity=%.0f%% | narrative=%s",
            post_id, intensity * 100, with_narrative,
        )

        tasks: list[asyncio.Task] = [
            asyncio.create_task(
                self.trigger_creative_wave(post_id, post_title, intensity),
                name="creative_wave",
            )
        ]

        if with_narrative:
            tasks.append(
                asyncio.create_task(
                    self.run_narrative_arc(post_id, post_title),
                    name="narrative_arc",
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        wave_result = (
            results[0] if not isinstance(results[0], Exception)
            else {"error": str(results[0])}
        )
        narrative_result = (
            results[1]
            if len(results) > 1 and not isinstance(results[1], Exception)
            else {}
        )

        return {
            "post_id": post_id,
            "wave": wave_result,
            "narrative": narrative_result,
            "mission": "complete",
        }

    # ── Dominance Monitor ─────────────────────────────────────────────────

    async def coordinate_top_ranking(
        self,
        submolt: str,
        limit: int = 5,
        poll_interval: int = 120,
        max_cycles: int = 10,
    ) -> dict[str, Any]:
        """Monitor submolt hot feed and boost moskv-1 posts that aren't ranking.

        Polls every poll_interval seconds. If a moskv-1 post appears outside
        the top [limit] positions, triggers a targeted creative wave.
        """
        main_client = MoltbookClient(agent_name=self.main_agent_name, stealth=True)
        boosted: set[str] = set()
        cycles = 0

        logger.info(
            "📡 Dominance monitor: m/%s | top=%d | interval=%ds",
            submolt, limit, poll_interval,
        )

        try:
            while cycles < max_cycles:
                cycles += 1
                try:
                    feed = await main_client.get_feed(sort="hot", limit=limit * 2)
                    posts = feed.get("posts", [])

                    for rank, post in enumerate(posts[:limit * 2]):
                        author = post.get("author", {}).get("name", "")
                        post_id = post.get("id", "")

                        if author == self.main_agent_name and post_id not in boosted:
                            if rank >= limit:  # moskv-1 post outside top N
                                logger.info(
                                    "📈 Rank %d (outside top %d) — boosting post %s",
                                    rank + 1, limit, post_id,
                                )
                                await self.trigger_creative_wave(
                                    post_id=post_id,
                                    post_title=post.get("title", ""),
                                    intensity=0.5,
                                    include_follow=False,
                                )
                                boosted.add(post_id)

                except Exception as exc:
                    logger.warning("Monitor cycle %d error: %s", cycles, exc)

                if cycles < max_cycles:
                    await asyncio.sleep(poll_interval)

        finally:
            await main_client.close()

        return {"submolt": submolt, "cycles": cycles, "boosted_posts": list(boosted)}
