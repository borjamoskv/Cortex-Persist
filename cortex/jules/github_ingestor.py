"""MOSKV-Jules — GitHub Issue ingestor.

Polls GitHub repositories for issues labeled 'jules' and enqueues them.
"""

from __future__ import annotations

import logging
from pathlib import Path

import httpx

from cortex.jules.models import AgentTask, TaskSource
from cortex.jules.queue import TaskQueue

__all__ = ["GitHubIngestor"]

logger = logging.getLogger("cortex.jules.github")

_GH_API = "https://api.github.com"
_LABEL = "jules"
_COMMENTED_LABEL = "jules:processing"


class GitHubIngestor:
    """Polls GitHub Issues labeled 'jules' and converts them to AgentTasks.

    Requires a GitHub Personal Access Token with `repo` scope.
    """

    def __init__(
        self,
        token: str,
        repos: list[str],
        queue: TaskQueue,
        default_repo_base: str = str(Path.home()),
    ) -> None:
        self._token = token
        self._repos = repos  # ["org/repo", ...]
        self._queue = queue
        self._default_repo_base = Path(default_repo_base)
        self._processed: set[int] = set()
        self._client = httpx.Client(
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=15.0,
        )

    def poll(self) -> int:
        """Fetch labeled issues and enqueue new ones. Returns count enqueued."""
        enqueued = 0
        for repo in self._repos:
            try:
                enqueued += self._poll_repo(repo)
            except httpx.HTTPError as e:
                logger.warning("GitHub poll failed for %s: %s", repo, e)
        return enqueued

    def _poll_repo(self, repo: str) -> int:
        """Poll a single repo. Returns count enqueued."""
        url = f"{_GH_API}/repos/{repo}/issues"
        resp = self._client.get(url, params={"labels": _LABEL, "state": "open", "per_page": 20})
        resp.raise_for_status()
        issues = resp.json()

        count = 0
        for issue in issues:
            issue_num = issue["number"]
            if issue_num in self._processed:
                continue

            # Check if already enqueued (via comment or label check)
            if any(label["name"] == _COMMENTED_LABEL for label in issue.get("labels", [])):
                self._processed.add(issue_num)
                continue

            task = self._issue_to_task(issue, repo)
            self._queue.enqueue(task)
            self._processed.add(issue_num)
            self._comment_on_issue(repo, issue_num, task.id)
            self._add_label(repo, issue_num, _COMMENTED_LABEL)
            logger.info("📥 Enqueued GitHub issue #%d from %s", issue_num, repo)
            count += 1

        return count

    def _issue_to_task(self, issue: dict, repo: str) -> AgentTask:
        """Convert a GitHub issue to an AgentTask."""
        # Try to find a local clone of the repo
        repo_name = repo.split("/")[-1]
        possible_paths = [
            self._default_repo_base / repo_name,
            Path.home() / repo_name,
            Path.home() / "projects" / repo_name,
            Path.home() / "code" / repo_name,
        ]
        repo_path = next((str(p) for p in possible_paths if p.exists()), str(Path.home()))

        body = issue.get("body") or ""
        description = f"{issue['title']}\n\n{body}".strip()

        return AgentTask(
            title=issue["title"][:120],
            description=description[:3000],
            repo_path=repo_path,
            source=TaskSource.GITHUB,
            github_issue_number=issue["number"],
            github_repo=repo,
        )

    def _comment_on_issue(self, repo: str, issue_num: int, task_id: str) -> None:
        try:
            self._client.post(
                f"{_GH_API}/repos/{repo}/issues/{issue_num}/comments",
                json={
                    "body": (
                        f"🤖 **MOSKV-Jules** picked up this issue. Task ID: `{task_id}`\n\n"
                        f"Working autonomously — branch `jules/{task_id}` will be created when done."
                    )
                },
            )
        except httpx.HTTPError as e:
            logger.debug("Comment failed: %s", e)

    def _add_label(self, repo: str, issue_num: int, label: str) -> None:
        try:
            self._client.post(
                f"{_GH_API}/repos/{repo}/issues/{issue_num}/labels",
                json={"labels": [label]},
            )
        except httpx.HTTPError as e:
            logger.debug("Label failed: %s", e)

    def close(self) -> None:
        self._client.close()
