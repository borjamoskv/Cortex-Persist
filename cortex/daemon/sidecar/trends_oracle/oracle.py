"""The Google Trends Oracle — permanent connection system."""

import asyncio
import logging
import random
import time
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from pytrends.request import TrendReq
from requests.exceptions import RequestException

from cortex.daemon.models import TrendsAlert
from cortex.daemon.sidecar.trends_oracle.config import TrendsConfig

logger = logging.getLogger("moskv-daemon")


class TrendsOracle:
    """Permanent connection sidecar for Google Trends."""

    def __init__(self, engine: Any, config: TrendsConfig):
        self.engine = engine
        self.config = config
        self.running = False

        # Initialize pytrends with basic config (hl='en-US' or target region)
        # Using a timeout to prevent hanging
        self.pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25))

        # In-memory dedup cache: "geo:category:type:keyword" -> expiry timestamp
        self._cache: dict[str, float] = {}

        # Keep track of latest alerts to hand off to the Monitor
        self._latest_alerts: list[TrendsAlert] = []

    def _is_cached(self, cache_key: str, now: float) -> bool:
        """Check if an item is recently processed."""
        expiry = self._cache.get(cache_key)
        if expiry and now < expiry:
            return True
        return False

    def _mark_cached(self, cache_key: str, now: float) -> None:
        """Mark item as processed with TTL."""
        self._cache[cache_key] = now + self.config.cache_ttl

    def _clean_cache(self, now: float) -> None:
        """Prune expired cache entries."""
        expired = [k for k, v in self._cache.items() if v <= now]
        for k in expired:
            del self._cache[k]

    async def run_loop(self) -> None:
        """Async main loop for the sidecar."""
        self.running = True
        logger.info("📈 [TRENDS_ORACLE] Activated. Monitoring global entropy (DEFCON 2).")

        # Keep track of individual cycle intervals
        last_realtime = 0.0
        last_daily = 0.0

        while self.running:
            try:
                now = time.monotonic()
                self._clean_cache(now)

                tasks = []
                # 1. Realtime trends (if enabled)
                if (
                    self.config.enable_realtime
                    and (now - last_realtime) >= self.config.realtime_interval
                ):
                    tasks.append(self._poll_realtime())
                    last_realtime = now

                # 2. Daily searches
                if (now - last_daily) >= self.config.daily_interval:
                    tasks.append(self._poll_daily())
                    last_daily = now

                if tasks:
                    await asyncio.gather(*tasks)

            except Exception as e:  # noqa: BLE001
                logger.error("❌ [TRENDS_ORACLE] Loop Error: %s", e)

            # Wait before the next check. A fast loop checking intervals.
            await asyncio.sleep(15.0)

    def run_sync_loop(self) -> None:
        """Synchronous loop for threaded environments (MoskvDaemon)."""
        logger.info("📈 [TRENDS_ORACLE] (Thread) started.")
        self.running = True

        last_realtime = 0.0
        last_daily = 0.0

        while self.running:
            try:
                now = time.monotonic()
                self._clean_cache(now)

                # 1. Realtime trends
                if (
                    self.config.enable_realtime
                    and (now - last_realtime) >= self.config.realtime_interval
                ):
                    self._poll_realtime_sync()
                    last_realtime = now

                # 2. Daily searches
                if (now - last_daily) >= self.config.daily_interval:
                    self._poll_daily_sync()
                    last_daily = now

            except Exception as e:  # noqa: BLE001
                logger.error("❌ [TRENDS_ORACLE] (Thread) Error: %s", e)

            time.sleep(15.0)

    def stop(self) -> None:
        """Gracefully stop the oracle loop."""
        self.running = False

    # -------------------------------------------------------------
    # Polling Logic wrappers (with synchronous pytrends backends)
    # -------------------------------------------------------------

    def _poll_realtime_sync(self):
        """Fetch and process realtime trending searches."""
        alerts = []
        now = time.monotonic()

        for geo in self.config.geos:
            target_geo = geo if geo else "US"  # pytrends requires a valid geo for realtime
            try:
                # pytrends realtime is sometimes fragile with pure empty geos
                df = self.pytrends.realtime_trending_searches(pn=target_geo)
                if df is not None and not df.empty:
                    # Dataframe schema varies, but usually: 'title', 'entityNames', 'articleUrls'
                    if "title" in df.columns:
                        for idx, row in df.iterrows():
                            # Limiting to top 20
                            if idx > 20:
                                break
                            title = str(row["title"])
                            traffic = "Rising (Realtime)"

                            cache_key = f"{geo}:realtime:{title}"
                            if not self._is_cached(cache_key, now):
                                alert = self._store_and_emit(title, traffic, geo, 0, "realtime")
                                if alert:
                                    alerts.append(alert)
                                self._mark_cached(cache_key, now)

            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "⚠️ [TRENDS_ORACLE] Realtime query failed for '%s': %s", target_geo, e
                )

        if alerts:
            self._latest_alerts = alerts
            logger.info("📈 [TRENDS_ORACLE] Processed %d new realtime trends.", len(alerts))

    def _poll_daily_sync(self):
        """Fetch and process daily trending searches."""
        alerts = []
        now = time.monotonic()

        for geo in self.config.geos:
            target_geo = geo if geo else "US"
            try:
                df = self.pytrends.trending_searches(pn=target_geo)
                if df is not None and not df.empty:
                    # 'df' has one column: 0 -> the term
                    for term in df[0][:15]:  # Take top 15
                        keyword = str(term)
                        traffic = "Trending Daily"

                        cache_key = f"{geo}:daily:{keyword}"
                        if not self._is_cached(cache_key, now):
                            alert = self._store_and_emit(keyword, traffic, geo, 0, "daily")
                            if alert:
                                alerts.append(alert)
                            self._mark_cached(cache_key, now)
            except Exception as e:  # noqa: BLE001
                logger.warning("⚠️ [TRENDS_ORACLE] Daily query failed for '%s': %s", target_geo, e)

        if alerts:
            self._latest_alerts.extend(alerts)
            # Keep array size manageable
            self._latest_alerts = self._latest_alerts[-50:]
            logger.info("📉 [TRENDS_ORACLE] Processed %d new daily trends.", len(alerts))

    async def _poll_realtime(self):
        await asyncio.to_thread(self._poll_realtime_sync)

    async def _poll_daily(self):
        await asyncio.to_thread(self._poll_daily_sync)

    # -------------------------------------------------------------
    # Explicit Queries (e.g. for CLI/Agents)
    # -------------------------------------------------------------

    def fetch_interest_over_time(
        self, keywords: list[str], geo: str = "", timeframe: str = "today 1-m"
    ) -> pd.DataFrame:
        """Fetch interest over time for specific keywords."""
        if not keywords:
            return pd.DataFrame()

        _execute_with_backoff(
            lambda: self.pytrends.build_payload(
                kw_list=keywords, cat=0, timeframe=timeframe, geo=geo
            ),
            max_retries=self.config.max_retries,
            base_backoff=self.config.base_backoff,
        )

        return _execute_with_backoff(
            self.pytrends.interest_over_time,
            max_retries=self.config.max_retries,
            base_backoff=self.config.base_backoff,
        )

    # -------------------------------------------------------------
    # CORTEX Persistence
    # -------------------------------------------------------------

    def _store_and_emit(
        self, keyword: str, traffic: str, geo: str, category: int, trend_type: str
    ) -> TrendsAlert | None:
        """Stores the trend as a CORTEX fact and creates a Daemon Alert."""
        iso_now = datetime.now(timezone.utc).isoformat()
        geo_str = geo if geo else "Global"

        # 1. Create Fact Payload
        meta = {
            "keyword": keyword,
            "traffic_volume": traffic,
            "geo": geo_str,
            "trend_type": trend_type,
            "category": category,
            "source": "oracle:trends",
        }

        content = f"Trending Search [{trend_type}]: {keyword} ({geo_str})"

        # 2. Store Fact Resiliently (if engine available)
        if self.engine and hasattr(self.engine, "store"):
            try:
                self.engine.store(
                    project="google-trends",
                    content=content,
                    fact_type="trend",
                    meta=meta,
                )
            except Exception as e:  # noqa: BLE001
                logger.error("⚙️ [TRENDS_ORACLE] DB lock o error almacenando fact: %s", e)
                # We still emit the alert even if storage failed

        # 3. Form Alert
        return TrendsAlert(
            keyword=keyword,
            traffic_volume=traffic,
            geo=geo_str,
            category=str(category),
            trend_type=trend_type,
            timestamp=iso_now,
        )

    def consume_alerts(self) -> list[TrendsAlert]:
        """Provides the pending alerts to the monitor and clears them."""
        alerts = self._latest_alerts.copy()
        self._latest_alerts.clear()
        return alerts


def _execute_with_backoff(func, max_retries: int = 3, base_backoff: float = 1.5):
    """Executes a pytrends call with exponential backoff on rate limits."""
    last_error = None
    for attempt in range(max_retries):
        try:
            return func()
        except RequestException as e:
            # 429 means Too Many Requests
            if "429" in str(e):
                delay = (base_backoff**attempt) + random.uniform(0.5, 2.5)
                logger.warning("⏳ [TRENDS_ORACLE] Rate limit (429). Retrying in %.1fs...", delay)
                time.sleep(delay)
                last_error = e
            else:
                # Re-raise other HTTP errors
                raise e

    logger.error("💀 [TRENDS_ORACLE] Failed after %d attempts: %s", max_retries, last_error)
    raise RuntimeError(f"Google Trends query failed: {last_error}") from last_error
