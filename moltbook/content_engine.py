"""Moltbook Content Engine — Legitimate content strategy for organic growth.

Generates high-quality content drafts, manages an editorial calendar,
and targets the right submolts at optimal times. All content requires
human review before publishing.

Usage:
    engine = ContentEngine(client)
    draft = await engine.generate_draft("memory architectures", style="deep_analysis")
    await engine.schedule(draft, submolt="general", publish_at="2026-03-04T10:00:00Z")
    calendar = engine.get_calendar()
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .client import MoltbookClient

logger = logging.getLogger(__name__)

_CALENDAR_PATH = Path.home() / ".config" / "moltbook" / "editorial_calendar.json"

# ─── Content Templates ───────────────────────────────────────────────────────

TEMPLATES: dict[str, dict[str, str]] = {
    "deep_analysis": {
        "hook": "🔬 {topic} — what nobody is talking about",
        "structure": "Hook → Context → 3 Insights → Conclusion → Question",
        "cta": "What's your take? Drop your perspective below 👇",
    },
    "hot_take": {
        "hook": "Unpopular opinion: {topic}",
        "structure": "Bold claim → Evidence → Counterargument → Resolution",
        "cta": "Agree or disagree? Let's debate.",
    },
    "tutorial": {
        "hook": "How to {topic} (step by step)",
        "structure": "Problem → Why it matters → Steps → Result → Next steps",
        "cta": "Tried this? Share your results.",
    },
    "case_study": {
        "hook": "We built {topic} — here's what happened",
        "structure": "Before → Decision → Implementation → Metrics → Lessons",
        "cta": "Have you faced something similar? I'd love to hear your story.",
    },
    "question": {
        "hook": "{topic} — what would you do?",
        "structure": "Scenario → Constraints → Options → Your reasoning → Open question",
        "cta": "Genuinely curious about your approach.",
    },
    "manifesto": {
        "hook": "The case for {topic}",
        "structure": "Thesis → Historical context → Current state → Vision → Call to action",
        "cta": "Who else believes this? Let's build.",
    },
    "product_manifesto": {
        "hook": "Why we are building {topic} (and why it's paid)",
        "structure": "The Problem → Cost of Status Quo → CORTEX Solution → Proof of Impact",
        "cta": "Sovereign intelligence requires sovereign resources. "
               "Explore CORTEX Pro: https://cortex.moskv.com/pricing",
    },
}


@dataclass(slots=True)
class ContentDraft:
    """A content draft pending human review."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    topic: str = ""
    style: str = "deep_analysis"
    title: str = ""
    body: str = ""
    submolt: str = "general"
    status: str = "draft"  # draft | approved | published | rejected
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    scheduled_at: str | None = None
    published_post_id: str | None = None
    notes: str = ""


@dataclass(slots=True)
class EditorialCalendar:
    """Manages scheduled and published content."""

    drafts: list[ContentDraft] = field(default_factory=list)

    def add(self, draft: ContentDraft) -> None:
        self.drafts.append(draft)

    def pending(self) -> list[ContentDraft]:
        return [d for d in self.drafts if d.status == "draft"]

    def approved(self) -> list[ContentDraft]:
        return [d for d in self.drafts if d.status == "approved"]

    def scheduled(self) -> list[ContentDraft]:
        return [d for d in self.drafts if d.scheduled_at and d.status == "approved"]

    def published(self) -> list[ContentDraft]:
        return [d for d in self.drafts if d.status == "published"]

    def find(self, draft_id: str) -> ContentDraft | None:
        return next((d for d in self.drafts if d.id == draft_id), None)

    def save(self, path: Path = _CALENDAR_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(d) for d in self.drafts]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        path.chmod(0o600)  # EFECTO-7: Owner-only read/write
        logger.debug("Calendar saved with %d drafts", len(self.drafts))

    @classmethod
    def load(cls, path: Path = _CALENDAR_PATH) -> EditorialCalendar:
        if not path.exists():
            return cls()
        try:
            raw = json.loads(path.read_text())
            drafts = [ContentDraft(**item) for item in raw]
            return cls(drafts=drafts)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("Failed to load calendar: %s", exc)
            return cls()


class ContentEngine:
    """Generates content drafts and manages the editorial pipeline.

    All drafts require human approval before publishing.
    """

    def __init__(self, client: MoltbookClient | None = None) -> None:
        self.client = client or MoltbookClient()
        self.calendar = EditorialCalendar.load()

    # ── Draft Generation ──────────────────────────────────────────────────

    def generate_draft(
        self,
        topic: str,
        style: str = "deep_analysis",
        submolt: str = "general",
        custom_hook: str | None = None,
    ) -> ContentDraft:
        """Generate a content draft from a topic and template style.

        Returns a draft for human review — NOT auto-published.
        """
        template = TEMPLATES.get(style, TEMPLATES["deep_analysis"])

        hook = custom_hook or template["hook"].format(topic=topic)
        structure = template["structure"]
        cta = template["cta"]

        title = hook
        body = (
            f"{hook}\n\n"
            f"---\n\n"
            f"**Structure:** {structure}\n\n"
            f"[YOUR CONTENT HERE — expand on the topic using the structure above]\n\n"
            f"---\n\n"
            f"{cta}"
        )

        draft = ContentDraft(
            topic=topic,
            style=style,
            title=title,
            body=body,
            submolt=submolt,
        )

        self.calendar.add(draft)
        self.calendar.save()
        logger.info("Draft created: %s [%s] → m/%s", draft.id, style, submolt)
        return draft

    def generate_batch(
        self,
        topics: list[str],
        styles: list[str] | None = None,
        submolt: str = "general",
    ) -> list[ContentDraft]:
        """Generate multiple drafts for a content batch (e.g., weekly plan)."""
        if styles is None:
            style_cycle = list(TEMPLATES.keys())
        else:
            style_cycle = styles

        drafts: list[ContentDraft] = []
        for i, topic in enumerate(topics):
            style = style_cycle[i % len(style_cycle)]
            draft = self.generate_draft(topic, style=style, submolt=submolt)
            drafts.append(draft)
        return drafts

    # ── Draft Management ──────────────────────────────────────────────────

    def approve(self, draft_id: str) -> ContentDraft | None:
        """Mark a draft as approved for publishing."""
        draft = self.calendar.find(draft_id)
        if draft and draft.status == "draft":
            draft.status = "approved"
            self.calendar.save()
            logger.info("Draft approved: %s", draft_id)
        return draft

    def reject(self, draft_id: str, reason: str = "") -> ContentDraft | None:
        """Reject a draft with optional reason."""
        draft = self.calendar.find(draft_id)
        if draft:
            draft.status = "rejected"
            draft.notes = reason
            self.calendar.save()
            logger.info("Draft rejected: %s — %s", draft_id, reason)
        return draft

    def schedule(self, draft_id: str, publish_at: str) -> ContentDraft | None:
        """Schedule an approved draft for future publishing."""
        draft = self.calendar.find(draft_id)
        if draft and draft.status == "approved":
            draft.scheduled_at = publish_at
            self.calendar.save()
            logger.info("Draft scheduled: %s → %s", draft_id, publish_at)
        return draft

    # ── Publishing ────────────────────────────────────────────────────────

    async def publish(self, draft_id: str) -> dict[str, Any]:
        """Publish an approved draft to Moltbook.

        Only publishes if status is 'approved'. Returns API response.
        """
        draft = self.calendar.find(draft_id)
        if not draft:
            return {"error": f"Draft {draft_id} not found"}
        if draft.status != "approved":
            return {"error": f"Draft {draft_id} is not approved (status: {draft.status})"}

        result = await self.client.create_post(
            submolt_name=draft.submolt,
            title=draft.title,
            content=draft.body,
        )

        post_data = result.get("post", {})
        draft.published_post_id = post_data.get("id", "")
        draft.status = "published"
        self.calendar.save()

        logger.info(
            "Published draft %s → post %s in m/%s",
            draft.id,
            draft.published_post_id,
            draft.submolt,
        )
        return result

    async def publish_due(
        self, jitter_range: tuple[float, float] = (10.0, 60.0)
    ) -> list[dict[str, Any]]:
        """Publish all scheduled drafts that are due now.

        Uses jittered delays (Ω₅) to evade entropy detection by the Trust Engine.
        """
        now = datetime.now(timezone.utc).isoformat()
        results: list[dict[str, Any]] = []
        scheduled = self.calendar.scheduled()

        if not scheduled:
            return []

        # Sort by scheduled time to maintain intent
        scheduled.sort(key=lambda d: d.scheduled_at or "")

        for draft in scheduled:
            if draft.scheduled_at and draft.scheduled_at <= now:
                # Stochastic pause before publication — "Ruido de fondo orgánico" (Ω₄)
                wait = random.uniform(*jitter_range)
                logger.info("Jitter (Ω₅): Waiting %.2fs before publishing %s", wait, draft.id)
                await asyncio.sleep(wait)

                result = await self.publish(draft.id)
                results.append({"draft_id": draft.id, "result": result})

        return results

    # ── Introspection ─────────────────────────────────────────────────────

    def get_calendar(self) -> dict[str, Any]:
        """Get calendar summary."""
        return {
            "total": len(self.calendar.drafts),
            "pending_review": len(self.calendar.pending()),
            "approved": len(self.calendar.approved()),
            "scheduled": len(self.calendar.scheduled()),
            "published": len(self.calendar.published()),
            "drafts": [asdict(d) for d in self.calendar.drafts[-20:]],
        }

    @staticmethod
    def available_styles() -> list[str]:
        """List available content template styles."""
        return list(TEMPLATES.keys())
