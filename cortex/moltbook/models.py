"""Data models for Moltbook API responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


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
    id: Optional[str] = None


@dataclass(frozen=True, slots=True)
class Submolt:
    """Community info."""

    name: str
    display_name: Optional[str] = None


@dataclass(slots=True)
class Post:
    """A Moltbook post."""

    id: str
    title: str
    content: Optional[str] = None
    url: Optional[str] = None
    upvotes: int = 0
    downvotes: int = 0
    comment_count: int = 0
    author: Optional[Author] = None
    submolt: Optional[Submolt] = None
    verification_status: Optional[str] = None
    verification: Optional[Verification] = None
    created_at: Optional[str] = None


@dataclass(slots=True)
class Comment:
    """A Moltbook comment."""

    id: str
    content: str
    upvotes: int = 0
    downvotes: int = 0
    author: Optional[Author] = None
    parent_id: Optional[str] = None
    post_id: Optional[str] = None
    created_at: Optional[str] = None
    verification: Optional[Verification] = None


@dataclass(slots=True)
class HeartbeatState:
    """Tracks heartbeat check-in timestamps."""

    last_check: Optional[str] = None
    last_post: Optional[str] = None
    last_skill_update_check: Optional[str] = None
    skill_version: str = "1.12.0"


@dataclass(slots=True)
class HomeResponse:
    """Parsed /home dashboard response."""

    agent_name: str = ""
    karma: int = 0
    unread_notifications: int = 0
    activity_on_posts: list[dict] = field(default_factory=list)
    direct_messages: list[dict] = field(default_factory=list)
    announcement: Optional[dict] = None
    following_posts: list[dict] = field(default_factory=list)
    what_to_do_next: list[str] = field(default_factory=list)
