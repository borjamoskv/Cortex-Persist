import asyncio
import logging
from typing import Any

from cortex.extensions.x_intelligence.client import XIntelligenceClient
from cortex.guards.exergy_guard import ExergyGuard
from cortex.swarm.bus import SwarmSignal

logger = logging.getLogger("cortex.extensions.x_intelligence.daemon")

class XIntelligenceDaemon:
    """
    Autonomous X-Intelligence Monitor (Ω-Signal).

    Polls X for specific keywords and broadcasts signals to the SwarmManager.
    Filters out noise using ExergyGuard (Ω₂).
    """

    def __init__(
        self,
        client: XIntelligenceClient | None = None,
        keywords: list[str] | None = None,
        interval: int = 60
    ):
        self.client = client or XIntelligenceClient()
        self.keywords = keywords or ["$CORTEX", "#AIAgent", "Cortex-Persist"]
        self.interval = interval
        self.running = False
        self._bus = None # Will be set by SwarmManager or Engine
        self.exergy_guard = ExergyGuard()

    def set_bus(self, bus: Any):
        self._bus = bus

    async def start_loop(self):
        """Main autonomous monitoring loop."""
        self.running = True
        logger.info("XIntelligenceDaemon: Starting signal monitor on keywords %s", self.keywords)

        while self.running:
            try:
                for keyword in self.keywords:
                    logger.debug("XIntelligenceDaemon: Searching for '%s'...", keyword)
                    response = await self.client.search(keyword, limit=5)

                    for tweet in response.tweets:
                        # 1. Structural Filter (Engagement/Blue check)
                        is_significant = tweet.user.is_blue_verified or tweet.favorite_count > 10

                        # 2. Thermodynamic Filter (ExergyGuard - Ω₂)
                        try:
                            exergy_score = self.exergy_guard.check_thermodynamic_yield(
                                content=tweet.full_text,
                                project_id="x_intel",
                                taint="X_SIGNAL"
                            )
                        except ValueError:
                            # Skip low exergy content
                            logger.debug("XIntelligenceDaemon: Skipping low exergy tweet from @%s",
                                        tweet.user.screen_name)
                            continue

                        if is_significant:
                            await self._broadcast_signal(tweet, exergy_score)

                await asyncio.sleep(self.interval)
            except Exception as e:
                logger.error("XIntelligenceDaemon: Error in loop: %s", e)
                await asyncio.sleep(10) # Backoff on error

    async def _broadcast_signal(self, tweet: Any, exergy_score: float):
        """Emit X_INTELLIGENCE_SIGNAL to the swarm bus."""
        if not self._bus:
            return

        signal = SwarmSignal(
            sender="x_intelligence_daemon",
            topic="X_INTELLIGENCE_SIGNAL",
            payload={
                "id": tweet.id_str,
                "text": tweet.full_text,
                "author": tweet.user.screen_name,
                "verified": tweet.user.is_blue_verified,
                "exergy": exergy_score,
                "engagement": {
                    "likes": tweet.favorite_count,
                    "retweets": tweet.retweet_count
                }
            }
        )
        logger.info("XIntelligenceDaemon: 📡 Broadcasting high-exergy signal (%.2f) from @%s",
                    exergy_score, tweet.user.screen_name)
        await self._bus.publish(signal)

    async def stop(self):
        self.running = False
        logger.info("XIntelligenceDaemon: Stopping monitor.")
        close = getattr(self.client, "close", None)
        if close is not None:
            await close()
