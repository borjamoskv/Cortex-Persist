"""Data models for Moltbook API responses."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class MoltbookCredentials:
    """Stored API credentials."""

    api_key: str
    agent_name: str


@dataclass(frozen=True, slots=True)
class Verification:
    """AI verification challenge from Moltbook."""

    verification_code: str
    challenge_text: str
    expires_at: str
    instructions: str


@dataclass(frozen=True, slots=True)
class Author:
    """Post/comment author."""

    name: str
    id: str | None = None


@dataclass(frozen=True, slots=True)
class Submolt:
    """Community info."""

    name: str
    display_name: str | None = None


@dataclass(slots=True)
class Post:
    """A Moltbook post."""

    id: str
    title: str
    content: str | None = None
    url: str | None = None
    upvotes: int = 0
    downvotes: int = 0
    comment_count: int = 0
    author: Author | None = None
    submolt: Submolt | None = None
    verification_status: str | None = None
    verification: Verification | None = None
    created_at: str | None = None


@dataclass(slots=True)
class Comment:
    """A Moltbook comment."""

    id: str
    content: str
    upvotes: int = 0
    downvotes: int = 0
    author: Author | None = None
    parent_id: str | None = None
    post_id: str | None = None
    created_at: str | None = None
    verification: Verification | None = None


@dataclass(slots=True)
class HeartbeatState:
    """Tracks heartbeat check-in timestamps."""

    last_check: str | None = None
    last_post: str | None = None
    last_skill_update_check: str | None = None
    skill_version: str = "1.12.0"


@dataclass(slots=True)
class HomeResponse:
    """Parsed /home dashboard response."""

    agent_name: str = ""
    karma: int = 0
    unread_notifications: int = 0
    activity_on_posts: list[dict] = field(default_factory=list)
    direct_messages: list[dict] = field(default_factory=list)
    announcement: dict | None = None
    following_posts: list[dict] = field(default_factory=list)
    what_to_do_next: list[str] = field(default_factory=list)
