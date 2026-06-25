# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX. Apache-2.0.
import pytest
from legacy_research.guards.scrape_guard import (
    ScrapeSanitizerGuard,
    MAX_RAW_PAGE_SIZE,
    CORTEX_TAINT_SIGNATURE,
)


def test_sanitize_happy_path():
    content = "Hello world"
    url = "https://example.com"
    payload = ScrapeSanitizerGuard.sanitize(content, url)

    assert payload.content == "Hello world"
    assert payload.metadata["source_url"] == url
    assert payload.metadata["cortex_taint"] == CORTEX_TAINT_SIGNATURE
    assert payload.taint == CORTEX_TAINT_SIGNATURE
    assert payload.metadata["agent_trust"] == "0.0"


def test_sanitize_empty_rejection():
    with pytest.raises(ValueError, match="Empty content"):
        ScrapeSanitizerGuard.sanitize("")
    with pytest.raises(ValueError, match="Empty content"):
        ScrapeSanitizerGuard.sanitize("   ")
    with pytest.raises(ValueError, match="Empty content"):
        ScrapeSanitizerGuard.sanitize(None)


def test_sanitize_truncation_boundary():
    # Exactly MAX_RAW_PAGE_SIZE
    content = "a" * MAX_RAW_PAGE_SIZE
    payload = ScrapeSanitizerGuard.sanitize(content)
    assert len(payload.content) == MAX_RAW_PAGE_SIZE
    assert payload.content == content

    # Exceeds MAX_RAW_PAGE_SIZE
    content = "a" * (MAX_RAW_PAGE_SIZE + 10)
    payload = ScrapeSanitizerGuard.sanitize(content)
    assert len(payload.content) == MAX_RAW_PAGE_SIZE
    assert payload.content == "a" * MAX_RAW_PAGE_SIZE


def test_sanitize_purgation():
    # Script removal
    content = "Safe<script>alert('xss')</script> text"
    payload = ScrapeSanitizerGuard.sanitize(content)
    assert "script" not in payload.content
    assert payload.content == "Safe text"

    # Iframe removal
    content = "Safe<iframe src='malicious.com'></iframe> text"
    payload = ScrapeSanitizerGuard.sanitize(content)
    assert "iframe" not in payload.content
    assert payload.content == "Safe text"

    # On-event removal
    content = '<div onclick="alert(1)" onmouseover="evil()">Safe</div>'
    payload = ScrapeSanitizerGuard.sanitize(content)
    assert "onclick" not in payload.content
    assert "onmouseover" not in payload.content
    assert payload.content == "<div>Safe</div>"


def test_sanitize_combined_malicious():
    content = """
    <script>evil()</script>
    <div onmouseover="run()">Content</div>
    <iframe src="bad"></iframe>
    """
    payload = ScrapeSanitizerGuard.sanitize(content)
    assert "script" not in payload.content
    assert "onmouseover" not in payload.content
    assert "iframe" not in payload.content
    assert "Content" in payload.content


def test_sanitize_no_url():
    payload = ScrapeSanitizerGuard.sanitize("some content")
    assert payload.metadata["source_url"] == "unknown"
