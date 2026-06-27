# [C5-REAL] Exergy-Maximized
import json
import logging
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class IssueContext:
    title: str
    body: str
    author: str
    labels: list[str] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)


class IssueReader:
    """
    Deterministic Issue Reader.
    Priority:
    1. GitHub API (if valid URL and accessible)
    2. HTML Parsing (fallback)
    3. Mac Maestro (future fallback)
    """

    @classmethod
    def read(cls, issue_url: str, github_token: str | None = None) -> IssueContext:
        """
        Reads a GitHub issue and returns structured IssueContext.
        """
        # Parse owner, repo, issue_number from URL
        # Example: https://github.com/borjamoskv/Cortex-Persist/issues/42
        match = re.match(r"https?://github\.com/([^/]+)/([^/]+)/issues/(\d+)", issue_url)
        if not match:
            raise ValueError(f"Invalid GitHub Issue URL: {issue_url}")

        owner, repo, issue_number = match.groups()

        # Try API First
        try:
            return cls._read_via_api(owner, repo, issue_number, github_token)
        except Exception as e:
            logger.warning(f"GitHub API failed for {issue_url}: {e}. Falling back to HTML...")

        # Try HTML Fallback
        try:
            return cls._read_via_html(issue_url)
        except Exception as e:
            logger.error(
                f"HTML Parsing failed for {issue_url}: {e}. Mac Maestro fallback not yet implemented."
            )
            raise RuntimeError(f"Could not extract issue data from {issue_url}")

    @classmethod
    def _read_via_api(
        cls, owner: str, repo: str, issue_number: str, token: str | None = None
    ) -> IssueContext:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "CORTEX-IssueReader/1.0",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        if not api_url.startswith("https://"):
            raise ValueError(f"Invalid API URL scheme: {api_url}")

        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:  # nosec B310
            data = json.loads(response.read().decode("utf-8"))

        title = data.get("title", "")
        body = data.get("body", "") or ""
        author = data.get("user", {}).get("login", "")
        labels = [label.get("name") for label in data.get("labels", [])]

        # Fetch comments if > 0
        comments = []
        comments_url = data.get("comments_url")
        if data.get("comments", 0) > 0 and comments_url:
            if not comments_url.startswith("https://"):
                raise ValueError(f"Invalid comments URL scheme: {comments_url}")
            req_comments = urllib.request.Request(comments_url, headers=headers)
            with urllib.request.urlopen(req_comments, timeout=10) as res_comments:  # nosec B310
                comments_data = json.loads(res_comments.read().decode("utf-8"))
                for comment in comments_data:
                    c_body = comment.get("body", "")
                    c_author = comment.get("user", {}).get("login", "")
                    if c_body:
                        comments.append(f"[{c_author}]: {c_body}")

        return IssueContext(title=title, body=body, author=author, labels=labels, comments=comments)

    @classmethod
    def _read_via_html(cls, issue_url: str) -> IssueContext:
        """
        Fallback HTML scraper (basic implementation).
        In production, this would use BeautifulSoup, but we keep dependencies zero for now.
        """
        if not (issue_url.startswith("https://") or issue_url.startswith("http://")):
            raise ValueError(f"Invalid issue URL scheme: {issue_url}")
        req = urllib.request.Request(issue_url, headers={"User-Agent": "CORTEX-IssueReader/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:  # nosec B310
            html = response.read().decode("utf-8")

        # Extremely basic regex parsing for fallback
        title_match = re.search(r"<title>(.*?)\s·\sIssue", html)
        title = title_match.group(1) if title_match else "Unknown Title"

        author_match = re.search(r"author[^>]*>([^<]+)</a>\s*opened this issue", html)
        author = author_match.group(1) if author_match else "Unknown Author"

        return IssueContext(
            title=title,
            body="[Body extraction requires API or robust DOM parsing. HTML fallback limited.]",
            author=author,
            labels=[],
            comments=[],
        )
