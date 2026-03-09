"""Tests for CORTEX Resilient Gateway — Ω₅ Antifragile URL cascade."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from cortex.mcp.resilient_gateway import (
    ResilientFetcher,
    _html_to_markdown,
    _extract_with_selector,
)
from cortex.utils.pulmones import CircuitBreaker


# ─── Fixtures ────────────────────────────────────────────────────────

SAMPLE_HTML = """
<html>
<head><title>Test</title></head>
<body>
<nav><a href="/">Home</a></nav>
<main>
<h1>Sovereign Gateway</h1>
<p>This is the main content about <strong>resilient systems</strong>.</p>
<div class="details"><p>Extra detail block.</p></div>
</main>
<script>var x = 1;</script>
<footer>Footer noise</footer>
</body>
</html>
"""


@pytest.fixture
def fetcher() -> ResilientFetcher:
    """Fresh fetcher with clean circuit breakers."""
    f = ResilientFetcher()
    for p in f._providers:
        p.circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
    return f


def _mock_provider_fn(fetcher: ResilientFetcher, name: str, mock: AsyncMock) -> None:
    """Replace a provider's fetch_fn with a mock by name."""
    for p in fetcher._providers:
        if p.name == name:
            p.fetch_fn = mock
            break


# ─── Test: Primary Success ──────────────────────────────────────────

class TestPrimarySuccess:
    """When httpx succeeds, no fallback is called."""

    @pytest.mark.asyncio
    async def test_primary_success_returns_content(self, fetcher: ResilientFetcher):
        mock_httpx = AsyncMock(return_value=(SAMPLE_HTML, 200))
        mock_aiohttp = AsyncMock(return_value=("<p>should not call</p>", 200))
        mock_urllib = AsyncMock(return_value=("<p>should not call</p>", 200))

        _mock_provider_fn(fetcher, "httpx", mock_httpx)
        _mock_provider_fn(fetcher, "aiohttp", mock_aiohttp)
        _mock_provider_fn(fetcher, "urllib", mock_urllib)

        result = await fetcher.fetch("https://example.com")

        assert result["status"] == "success"
        assert result["provider"] == "httpx"
        assert result["cascade_depth"] == 1
        assert "Sovereign Gateway" in result["content"]
        mock_httpx.assert_awaited_once()
        mock_aiohttp.assert_not_awaited()


# ─── Test: Primary Fail → Fallback Success ──────────────────────────

class TestFallbackCascade:
    """When httpx fails with 503, aiohttp takes over."""

    @pytest.mark.asyncio
    async def test_httpx_503_aiohttp_succeeds(self, fetcher: ResilientFetcher):
        mock_httpx = AsyncMock(side_effect=Exception("503 Service Unavailable"))
        mock_aiohttp = AsyncMock(return_value=(SAMPLE_HTML, 200))
        mock_urllib = AsyncMock(return_value=("<p>should not call</p>", 200))

        _mock_provider_fn(fetcher, "httpx", mock_httpx)
        _mock_provider_fn(fetcher, "aiohttp", mock_aiohttp)
        _mock_provider_fn(fetcher, "urllib", mock_urllib)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await fetcher.fetch("https://example.com")

        assert result["status"] == "success"
        assert result["provider"] == "aiohttp"
        assert result["cascade_depth"] == 2
        assert len(result["errors"]) == 1
        assert "503" in result["errors"][0]
        mock_aiohttp.assert_awaited_once()
        mock_urllib.assert_not_awaited()


# ─── Test: Full Cascade Exhausted ───────────────────────────────────

class TestCascadeExhausted:
    """When ALL providers fail, returns error trace."""

    @pytest.mark.asyncio
    async def test_all_fail_returns_cascade_exhausted(self, fetcher: ResilientFetcher):
        _mock_provider_fn(fetcher, "httpx", AsyncMock(side_effect=Exception("httpx: refused")))
        _mock_provider_fn(fetcher, "aiohttp", AsyncMock(side_effect=Exception("aiohttp: DNS fail")))
        _mock_provider_fn(fetcher, "urllib", AsyncMock(side_effect=Exception("urllib: SSL error")))

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await fetcher.fetch("https://unreachable.invalid")

        assert result["status"] == "cascade_exhausted"
        assert result["content"] is None
        assert len(result["errors"]) == 3
        assert "httpx" in result["errors"][0]
        assert "aiohttp" in result["errors"][1]
        assert "urllib" in result["errors"][2]


# ─── Test: Circuit Breaker Skips Failed Provider ────────────────────

class TestCircuitBreaker:
    """After threshold failures, provider is skipped automatically."""

    @pytest.mark.asyncio
    async def test_open_circuit_skips_provider(self, fetcher: ResilientFetcher):
        # Force httpx circuit breaker open
        for _ in range(3):
            fetcher._providers[0].circuit_breaker.record_failure()
        assert fetcher._providers[0].circuit_breaker.state == "OPEN"

        mock_httpx = AsyncMock(return_value=("<p>must not call</p>", 200))
        mock_aiohttp = AsyncMock(return_value=(SAMPLE_HTML, 200))

        _mock_provider_fn(fetcher, "httpx", mock_httpx)
        _mock_provider_fn(fetcher, "aiohttp", mock_aiohttp)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await fetcher.fetch("https://example.com")

        # httpx should NOT have been called (circuit open)
        mock_httpx.assert_not_awaited()
        assert result["status"] == "success"
        assert result["provider"] == "aiohttp"
        assert "circuit open" in result["errors"][0].lower()


# ─── Test: CSS Selector Extraction ──────────────────────────────────

class TestCssExtraction:
    """Content extraction via CSS selectors."""

    def test_extract_with_selector_filters_content(self):
        result = _extract_with_selector(SAMPLE_HTML, ".details")
        assert "Extra detail" in result
        assert "Sovereign Gateway" not in result

    def test_extract_with_invalid_selector_degrades(self):
        result = _extract_with_selector(SAMPLE_HTML, ".nonexistent")
        assert "Sovereign Gateway" in result


# ─── Test: Markdown Conversion ──────────────────────────────────────

class TestMarkdownConversion:
    """HTML is properly cleaned and converted to markdown."""

    def test_strips_noise_elements(self):
        md = _html_to_markdown(SAMPLE_HTML)
        assert "var x" not in md
        assert "Footer noise" not in md
        assert "Sovereign Gateway" in md
        assert "resilient systems" in md

    def test_prefers_main_element(self):
        html = "<html><body><div>Noise</div><main><p>Core</p></main></body></html>"
        md = _html_to_markdown(html)
        assert "Core" in md

    def test_empty_html(self):
        md = _html_to_markdown("")
        assert isinstance(md, str)
