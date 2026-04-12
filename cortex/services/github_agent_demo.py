"""Shared one-shot harness for running the GitHubAgent against the current repository."""

from __future__ import annotations

from typing import Any

from cortex.services.github_agent_session import GitHubAgentSession

__all__ = ["build_github_agent_payload", "run_github_agent_demo"]

_OP_FIELDS: dict[str, frozenset[str]] = {
    "status": frozenset(),
    "dev": frozenset({"path"}),
    "permalink": frozenset({"path", "lines"}),
    "search": frozenset({"query", "path", "language", "symbol", "all_repos"}),
    "diff_url": frozenset({"pr_number", "commit_sha", "format_name"}),
    "review": frozenset({"pr_number"}),
    "blame": frozenset({"path", "ref"}),
    "history": frozenset({"path", "ref"}),
    "repo_clone": frozenset({"name_with_owner", "directory"}),
    "pr_checkout": frozenset({"pr_number"}),
    "pr_view": frozenset({"pr_number", "web"}),
    "pr_create": frozenset({"title", "body", "base", "head", "draft", "fill", "web"}),
}


def build_github_agent_payload(
    *,
    op: str,
    remote: str = "origin",
    **kwargs: Any,
) -> dict[str, Any]:
    """Build a TASK_REQUEST payload for the GitHubAgent, dropping null values."""
    payload: dict[str, Any] = {
        "op": op,
        "remote": remote,
    }
    allowed_keys = _OP_FIELDS.get(op)
    for key, value in kwargs.items():
        if value is None:
            continue
        if value == "":
            continue
        if isinstance(value, bool) and not value:
            continue
        if allowed_keys is not None and key not in allowed_keys:
            continue
        payload[key] = value
    return payload


async def run_github_agent_demo(
    payload: dict[str, Any],
    *,
    timeout: float = 5.0,
) -> dict[str, Any]:
    """Run GitHubAgent once and return its reply payload."""
    async with GitHubAgentSession(caller_id="demo-caller") as session:
        return await session.request(payload, timeout=timeout)
