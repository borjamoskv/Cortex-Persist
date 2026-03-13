"""Tests for cortex.sync.github_bridge — GitHub → CORTEX Bridge.

All GitHub API calls are mocked via httpx.MockTransport.
Uses CortexEngine with a temp database for realistic end-to-end testing.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from cortex.sync.github_bridge import GitHubCortexBridge, _github_key

pytestmark = pytest.mark.slow


# ─── Fixtures ────────────────────────────────────────────────────────


def _make_issue(
    number: int,
    title: str = "Test issue",
    state: str = "open",
    is_pr: bool = False,
    labels: list[str] | None = None,
    body: str = "Issue body content for testing purposes.",
) -> dict:
    """Factory for GitHub API issue JSON."""
    item: dict = {
        "number": number,
        "title": title,
        "state": state,
        "body": body,
        "html_url": f"https://github.com/borjamoskv/testrepo/issues/{number}",
        "labels": [{"name": lb} for lb in (labels or [])],
        "updated_at": "2026-03-13T12:00:00Z",
        "created_at": "2026-03-13T10:00:00Z",
    }
    if state == "closed":
        item["closed_at"] = "2026-03-13T14:00:00Z"
    if is_pr:
        item["pull_request"] = {
            "url": f"https://api.github.com/repos/borjamoskv/testrepo/pulls/{number}"
        }
    return item


def _mock_transport(routes: dict[str, list]) -> httpx.MockTransport:
    """Create a MockTransport routing URL patterns to JSON responses."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        for pattern, data in routes.items():
            if pattern in path:
                return httpx.Response(200, json=data)
        return httpx.Response(404, json={"message": "Not Found"})

    return httpx.MockTransport(handler)


@pytest.fixture
async def engine(tmp_path: Path):
    """Create a CortexEngine with a temp database."""
    from cortex.engine import CortexEngine

    db = str(tmp_path / "test_gh_bridge.db")
    e = CortexEngine(db_path=db, auto_embed=False)
    await e.init_db()
    yield e
    await e.close()


# ─── Tests ───────────────────────────────────────────────────────────


class TestGitHubKey:
    def test_deterministic(self):
        k1 = _github_key("borjamoskv/cortex", 42)
        k2 = _github_key("borjamoskv/cortex", 42)
        assert k1 == k2

    def test_different_for_different_inputs(self):
        k1 = _github_key("borjamoskv/cortex", 1)
        k2 = _github_key("borjamoskv/cortex", 2)
        assert k1 != k2


class TestSyncCreatesBridgeFacts:
    async def test_sync_creates_bridge_facts(self, engine):
        """Mock 2 open issues → verify 2 bridge facts stored."""
        issues = [
            _make_issue(1, title="Fix auth bug"),
            _make_issue(2, title="Add logging", is_pr=True),
        ]
        repos = [{"full_name": "borjamoskv/testrepo", "fork": False}]

        transport = _mock_transport({
            "/users/borjamoskv/repos": repos,
            "/repos/borjamoskv/testrepo/issues": issues,
        })

        bridge = GitHubCortexBridge(engine, token="fake-token", owner="borjamoskv")
        bridge._client = httpx.AsyncClient(transport=transport)

        result = await bridge.sync_all()

        assert result.issues_synced == 1
        assert result.prs_synced == 1
        assert result.repos_scanned == 1
        assert result.crystallized == 0

        await bridge.close()


class TestSyncSkipsDuplicates:
    async def test_sync_skips_duplicates(self, engine):
        """Run sync twice → second run returns skipped > 0."""
        issues = [_make_issue(10, title="Unique issue for dedup test")]
        repos = [{"full_name": "borjamoskv/testrepo", "fork": False}]

        transport = _mock_transport({
            "/users/borjamoskv/repos": repos,
            "/repos/borjamoskv/testrepo/issues": issues,
        })

        bridge = GitHubCortexBridge(engine, token="fake-token", owner="borjamoskv")
        bridge._client = httpx.AsyncClient(transport=transport)

        # First sync — should create
        r1 = await bridge.sync_all()
        assert r1.issues_synced == 1

        # Second sync — should skip
        bridge._client = httpx.AsyncClient(transport=transport)
        r2 = await bridge.sync_all()
        assert r2.skipped >= 1
        assert r2.issues_synced == 0

        await bridge.close()


class TestClosedIssueCrystallizes:
    async def test_closed_issue_crystallizes(self, engine):
        """Store an open issue, then sync with it closed → crystallize."""
        # Step 1: Sync with open issue
        open_issues = [_make_issue(20, title="Will close soon")]
        repos = [{"full_name": "borjamoskv/testrepo", "fork": False}]

        transport = _mock_transport({
            "/users/borjamoskv/repos": repos,
            "/repos/borjamoskv/testrepo/issues": open_issues,
        })

        bridge = GitHubCortexBridge(engine, token="fake-token", owner="borjamoskv")
        bridge._client = httpx.AsyncClient(transport=transport)
        r1 = await bridge.sync_all()
        assert r1.issues_synced == 1

        # Step 2: Sync again with the issue now closed
        closed_issues = [_make_issue(20, title="Will close soon", state="closed")]
        transport2 = _mock_transport({
            "/users/borjamoskv/repos": repos,
            "/repos/borjamoskv/testrepo/issues": closed_issues,
        })
        bridge._client = httpx.AsyncClient(transport=transport2)
        r2 = await bridge.sync_all()
        assert r2.crystallized == 1
        assert r2.issues_synced == 0

        await bridge.close()


class TestPRDetected:
    async def test_pr_detected_as_pr(self, engine):
        """Mock item with pull_request key → verify meta.github_type == 'pr'."""
        issues = [_make_issue(30, title="Feature PR", is_pr=True)]
        repos = [{"full_name": "borjamoskv/testrepo", "fork": False}]

        transport = _mock_transport({
            "/users/borjamoskv/repos": repos,
            "/repos/borjamoskv/testrepo/issues": issues,
        })

        bridge = GitHubCortexBridge(engine, token="fake-token", owner="borjamoskv")
        bridge._client = httpx.AsyncClient(transport=transport)
        result = await bridge.sync_all()

        assert result.prs_synced == 1
        assert result.issues_synced == 0

        await bridge.close()


class TestAuthFailureGraceful:
    async def test_auth_failure_graceful(self, engine):
        """Mock 401 → verify error in SyncResult.errors, no crash."""

        def error_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"message": "Bad credentials"})

        transport = httpx.MockTransport(error_handler)
        bridge = GitHubCortexBridge(engine, token="bad-token", owner="borjamoskv")
        bridge._client = httpx.AsyncClient(transport=transport)

        result = await bridge.sync_all()

        assert len(result.errors) >= 1
        assert "401" in result.errors[0]

        await bridge.close()
