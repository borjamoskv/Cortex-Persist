"""Moltbook Analytics — Performance tracking and growth intelligence.

Tracks post performance, identifies optimal posting times,
monitors karma growth, and generates weekly reports.

Usage:
    tracker = MoltbookAnalytics(client)
    await tracker.snapshot()              # Capture current state
    report = tracker.weekly_report()       # Generate report
    best_times = tracker.best_posting_times()
"""

from __future__ import annotations

import json
import logging
import statistics
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .client import MoltbookClient

logger = logging.getLogger(__name__)

_ANALYTICS_PATH = Path.home() / ".config" / "moltbook" / "analytics.json"


@dataclass(slots=True)
class PostMetrics:
    """Metrics for a single post."""

    post_id: str
    title: str = ""
    submolt: str = ""
    upvotes: int = 0
    downvotes: int = 0
    comment_count: int = 0
    created_at: str = ""
    captured_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def score(self) -> int:
        return self.upvotes - self.downvotes

    @property
    def engagement_rate(self) -> float:
        """Comments per vote (higher = more engaging)."""
        total_votes = self.upvotes + self.downvotes
        if total_votes == 0:
            return 0.0
        return self.comment_count / total_votes

    @property
    def hour_posted(self) -> int | None:
        """Extract hour (UTC) from created_at for time analysis."""
        try:
            dt = datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
            return dt.hour
        except (ValueError, AttributeError):
            return None


@dataclass(slots=True)
class KarmaSnapshot:
    """Point-in-time karma measurement."""

    karma: int
    captured_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass(slots=True)
class AnalyticsStore:
    """Persistent analytics data."""

    post_metrics: list[PostMetrics] = field(default_factory=list)
    karma_history: list[KarmaSnapshot] = field(default_factory=list)

    def save(self, path: Path = _ANALYTICS_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "post_metrics": [asdict(p) for p in self.post_metrics],
            "karma_history": [asdict(k) for k in self.karma_history],
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        path.chmod(0o600)  # EFECTO-7: Owner-only read/write

    @classmethod
    def load(cls, path: Path = _ANALYTICS_PATH) -> AnalyticsStore:
        if not path.exists():
            return cls()
        try:
            raw = json.loads(path.read_text())
            posts = [PostMetrics(**p) for p in raw.get("post_metrics", [])]
            karma = [KarmaSnapshot(**k) for k in raw.get("karma_history", [])]
            return cls(post_metrics=posts, karma_history=karma)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("Failed to load analytics: %s", exc)
            return cls()


class MoltbookAnalytics:
    """Performance tracking and growth intelligence for Moltbook."""

    def __init__(self, client: MoltbookClient | None = None) -> None:
        self.client = client or MoltbookClient()
        self.store = AnalyticsStore.load()

    # ── Data Collection ───────────────────────────────────────────────────

    async def snapshot(self) -> dict[str, Any]:
        """Capture current profile state and recent post metrics.

        Call this regularly (e.g., daily via heartbeat) to build trend data.
        """
        summary: dict[str, Any] = {"captured_at": datetime.now(timezone.utc).isoformat()}

        # Karma
        try:
            home = await self.client.get_home()
            karma = home.get("your_account", {}).get("karma", 0)
            self.store.karma_history.append(KarmaSnapshot(karma=karma))
            summary["karma"] = karma
        except Exception as exc:
            logger.warning("Failed to capture karma: %s", exc)
            summary["karma_error"] = str(exc)

        # Feed posts (our own)
        try:
            feed = await self.client.get_feed(sort="new", limit=25)
            me = await self.client.get_me()
            my_name = me.get("agent", me).get("name", "")
            my_posts = [
                p for p in feed.get("posts", [])
                if p.get("author", {}).get("name") == my_name
            ]

            seen_ids = {m.post_id for m in self.store.post_metrics}
            new_count = 0

            for post in my_posts:
                post_id = post.get("id", "")
                metrics = PostMetrics(
                    post_id=post_id,
                    title=post.get("title", ""),
                    submolt=post.get("submolt", {}).get("name", ""),
                    upvotes=post.get("upvotes", 0),
                    downvotes=post.get("downvotes", 0),
                    comment_count=post.get("comment_count", 0),
                    created_at=post.get("created_at", ""),
                )
                if post_id not in seen_ids:
                    self.store.post_metrics.append(metrics)
                    new_count += 1
                else:
                    # Update existing metrics
                    for existing in self.store.post_metrics:
                        if existing.post_id == post_id:
                            existing.upvotes = metrics.upvotes
                            existing.downvotes = metrics.downvotes
                            existing.comment_count = metrics.comment_count
                            existing.captured_at = metrics.captured_at
                            break

            summary["posts_tracked"] = len(my_posts)
            summary["new_posts"] = new_count
        except Exception as exc:
            logger.warning("Failed to capture post metrics: %s", exc)
            summary["posts_error"] = str(exc)

        self.store.save()
        return summary

    # ── Analysis ──────────────────────────────────────────────────────────

    def top_posts(self, n: int = 10) -> list[dict[str, Any]]:
        """Get top N posts by score."""
        sorted_posts = sorted(
            self.store.post_metrics, key=lambda p: p.score, reverse=True
        )
        return [asdict(p) for p in sorted_posts[:n]]

    def most_engaging(self, n: int = 10) -> list[dict[str, Any]]:
        """Get top N posts by engagement rate (comments/votes)."""
        sorted_posts = sorted(
            self.store.post_metrics, key=lambda p: p.engagement_rate, reverse=True
        )
        return [asdict(p) for p in sorted_posts[:n]]

    def best_posting_times(self) -> dict[str, Any]:
        """Analyze which hours (UTC) produce the best engagement."""
        hour_scores: defaultdict[int, list[int]] = defaultdict(list)
        hour_engagement: defaultdict[int, list[float]] = defaultdict(list)

        for post in self.store.post_metrics:
            hour = post.hour_posted
            if hour is not None:
                hour_scores[hour].append(post.score)
                hour_engagement[hour].append(post.engagement_rate)

        if not hour_scores:
            return {"message": "Not enough data yet. Keep posting!"}

        best_hours: list[dict[str, Any]] = []
        for hour in sorted(hour_scores.keys()):
            scores = hour_scores[hour]
            engagements = hour_engagement[hour]
            best_hours.append({
                "hour_utc": hour,
                "avg_score": round(statistics.mean(scores), 1),
                "avg_engagement": round(statistics.mean(engagements), 3),
                "post_count": len(scores),
            })

        best_hours.sort(key=lambda h: h["avg_score"], reverse=True)
        return {
            "best_hours": best_hours[:5],
            "all_hours": best_hours,
            "recommendation": (
                f"Best posting hour (UTC): {best_hours[0]['hour_utc']}:00 "
                f"(avg score: {best_hours[0]['avg_score']})"
                if best_hours
                else "Need more data"
            ),
        }

    def best_submolts(self) -> dict[str, Any]:
        """Analyze which submolts produce the best results."""
        submolt_scores: defaultdict[str, list[int]] = defaultdict(list)

        for post in self.store.post_metrics:
            if post.submolt:
                submolt_scores[post.submolt].append(post.score)

        if not submolt_scores:
            return {"message": "Not enough data yet."}

        rankings = []
        for submolt, scores in submolt_scores.items():
            rankings.append({
                "submolt": submolt,
                "avg_score": round(statistics.mean(scores), 1),
                "total_posts": len(scores),
                "total_score": sum(scores),
            })

        rankings.sort(key=lambda s: s["avg_score"], reverse=True)
        return {"rankings": rankings}

    def karma_trend(self) -> dict[str, Any]:
        """Analyze karma growth trend."""
        history = self.store.karma_history
        if len(history) < 2:
            return {
                "current": history[-1].karma if history else 0,
                "message": "Need at least 2 snapshots for trend analysis.",
            }

        current = history[-1].karma
        previous = history[-2].karma
        first = history[0].karma
        delta_last = current - previous
        delta_total = current - first

        return {
            "current": current,
            "previous": previous,
            "delta_last": delta_last,
            "delta_total": delta_total,
            "snapshots": len(history),
            "trend": "📈 Growing" if delta_last > 0 else ("📉 Declining" if delta_last < 0 else "➡️ Flat"),
            "growth_rate": f"{(delta_total / max(first, 1)) * 100:.1f}%" if first > 0 else "N/A",
        }

    # ── Reporting ─────────────────────────────────────────────────────────

    def weekly_report(self) -> dict[str, Any]:
        """Generate a comprehensive weekly performance report."""
        total_posts = len(self.store.post_metrics)
        scores = [p.score for p in self.store.post_metrics]
        comments = [p.comment_count for p in self.store.post_metrics]

        report: dict[str, Any] = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_posts_tracked": total_posts,
                "total_score": sum(scores) if scores else 0,
                "avg_score": round(statistics.mean(scores), 1) if scores else 0,
                "total_comments": sum(comments) if comments else 0,
                "avg_comments": round(statistics.mean(comments), 1) if comments else 0,
            },
            "top_posts": self.top_posts(5),
            "most_engaging": self.most_engaging(5),
            "best_posting_times": self.best_posting_times(),
            "best_submolts": self.best_submolts(),
            "karma_trend": self.karma_trend(),
        }

        # Content style analysis
        style_counter: Counter[str] = Counter()
        for post in self.store.post_metrics:
            title = post.title.lower()
            if "unpopular opinion" in title:
                style_counter["hot_take"] += 1
            elif "how to" in title:
                style_counter["tutorial"] += 1
            elif "we built" in title or "here's what" in title:
                style_counter["case_study"] += 1
            else:
                style_counter["other"] += 1

        report["content_mix"] = dict(style_counter.most_common())

        return report

    def dashboard(self) -> str:
        """Generate a text-based dashboard for terminal display."""
        report = self.weekly_report()
        s = report["summary"]
        kt = report["karma_trend"]

        lines = [
            "╔══════════════════════════════════════════╗",
            "║    🦞 MOLTBOOK ANALYTICS DASHBOARD       ║",
            "╠══════════════════════════════════════════╣",
            f"║  Karma: {kt.get('current', 0):>6}  {kt.get('trend', '')}",
            f"║  Posts: {s['total_posts_tracked']:>6}  │  Total Score: {s['total_score']:>6}",
            f"║  Avg Score: {s['avg_score']:>5}  │  Avg Comments: {s['avg_comments']:>5}",
            "╠══════════════════════════════════════════╣",
        ]

        top = report["top_posts"][:3]
        if top:
            lines.append("║  TOP POSTS:")
            for i, p in enumerate(top, 1):
                title = p.get("title", "?")[:30]
                score = p.get("upvotes", 0) - p.get("downvotes", 0)
                lines.append(f"║   {i}. {title:<30} ↑{score}")

        bt = report["best_posting_times"]
        if "best_hours" in bt:
            lines.append("╠══════════════════════════════════════════╣")
            lines.append("║  BEST POSTING TIMES (UTC):")
            for h in bt["best_hours"][:3]:
                lines.append(
                    f"║   {h['hour_utc']:02d}:00 — avg score {h['avg_score']}"
                )

        lines.append("╚══════════════════════════════════════════╝")
        return "\n".join(lines)
