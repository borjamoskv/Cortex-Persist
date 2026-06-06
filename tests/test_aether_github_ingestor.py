# [C5-REAL] Exergy-Maximized
from __future__ import annotations

from pathlib import Path

import httpx

from cortex.extensions.aether.github_ingestor import GitHubIngestor
from cortex.extensions.aether.queue import TaskQueue


def _issue(number: int, title: str, repo: str) -> dict:
    return {
        "number": number,
        "title": title,
        "body": f"Body for {repo}#{number}",
        "labels": [{"name": "aether"}],
        "html_url": f"https://github.com/{repo}/issues/{number}",
    }


def test_poll_dedupes_per_repo_not_globally(tmp_path: Path) -> None:
    queue = TaskQueue(tmp_path / "aether.db")

    routes = {
        "/repos/org/repo-one/issues": [_issue(1, "Repo one issue", "org/repo-one")],
        "/repos/org/repo-two/issues": [_issue(1, "Repo two issue", "org/repo-two")],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "GET":
            for route, payload in routes.items():
                if path == route:
                    return httpx.Response(200, json=payload)
        if request.method == "POST":
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(404, json={"message": "Not Found"})

    ingestor = GitHubIngestor(
        token="fake-token",
        repos=["org/repo-one", "org/repo-two"],
        queue=queue,
        default_repo_base=str(tmp_path),
    )
    ingestor._client = httpx.Client(transport=httpx.MockTransport(handler))

    try:
        enqueued = ingestor.poll()
    finally:
        ingestor.close()

    tasks = queue.list_tasks(limit=10)

    assert enqueued == 2
    assert len(tasks) == 2
    assert sorted(task.github_repo for task in tasks) == ["org/repo-one", "org/repo-two"]
    assert sorted(task.github_issue_number for task in tasks) == [1, 1]
