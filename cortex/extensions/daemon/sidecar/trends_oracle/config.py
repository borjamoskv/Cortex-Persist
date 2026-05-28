"""Configuration for the Google Trends Oracle."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TrendsConfig:
    """Configuration for the Google Trends Oracle sidecar."""

    # Keywords to permanently track (Interest Over Time)
    watchlist: list[str] = field(default_factory=list)

    # Geos to query. '' corresponds to global. 'US', 'ES', etc.
    geos: list[str] = field(default_factory=lambda: [""])

    # Categories to filter by. 0 is all categories.
    categories: list[int] = field(default_factory=lambda: [0])

    # Polling intervals in seconds
    realtime_interval: int = 900  # 15 minutes by default
    daily_interval: int = 21600  # 6 hours by default
    interest_interval: int = 86400  # 24 hours by default

    # Fault tolerance
    max_retries: int = 3
    base_backoff: float = 1.5

    # Memory and Deduplication
    cache_ttl: int = 3600  # 1 hour deduplication window

    # Enable fetching realtime trending searches
    enable_realtime: bool = True
