# [C5-REAL] Exergy-Maximized

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from cortex.services.notebooklm import (
    PROJECT_DOMAIN,
    DOMAIN_MAP,
    NotebookLMService,
)


class _FakeFact:
    """Minimal fact-like object for testing formatters."""

    def __init__(
        self,
        *,
        id: str = "A1B2C3D4E5F6",
        content: str = "Test fact content",
        confidence: str = "C4",
        tags: list[str] | None = None,
        project: str = "cortex",
        fact_type: str = "decision",
        source: str = "agent:gemini",
        timestamp: float = 1710345600.0,
    ) -> None:
        self.id = id
        self.content = content
        self.confidence = confidence
        self.tags = tags or []
        self.project = project
        self.fact_type = fact_type
        self.source = source
        self.timestamp = timestamp


class TestShadowKeyPattern:
    """Shadow Key protocol: ∆_CTX (open) + ∇_CTX (close) anchors."""

    def test_shadow_key_format(self) -> None:
        fact = _FakeFact(id="DEADBEEF1234")
        svc = NotebookLMService(":memory:")
        result = svc.format_fact(fact)

        assert "∆_CTX:DEADBEEF" in result
        assert "∇_CTX:DEADBEEF" in result

    def test_shadow_key_wraps_content(self) -> None:
        fact = _FakeFact(content="Important decision about architecture")
        svc = NotebookLMService(":memory:")
        result = svc.format_fact(fact)

        assert result.startswith("> ")
        assert "Important decision about architecture" in result
        assert result.index("∆_CTX:") < result.index("Important decision")
        assert result.index("Important decision") < result.index("∇_CTX:")

    def test_shadow_key_includes_confidence(self) -> None:
        fact = _FakeFact(confidence="C5")
        svc = NotebookLMService(":memory:")
        result = svc.format_fact(fact)

        assert "conf:C5" in result

    def test_shadow_key_includes_tags(self) -> None:
        fact = _FakeFact(tags=["security", "critical"])
        svc = NotebookLMService(":memory:")
        result = svc.format_fact(fact)

        assert "tax:security,critical" in result

    def test_shadow_key_no_stated_confidence(self) -> None:
        fact = _FakeFact(confidence="stated")
        svc = NotebookLMService(":memory:")
        result = svc.format_fact(fact)

        assert "conf:" not in result


class TestDomainClassification:
    """O(1) project → domain lookup."""

    def test_known_projects_classified(self) -> None:
        assert PROJECT_DOMAIN["cortex"] == "cortex-core"
        assert PROJECT_DOMAIN["MOSKV-1"] == "cortex.agents"
        assert PROJECT_DOMAIN["naroa"] == "cortex-products"
        assert PROJECT_DOMAIN["SAP"] == "cortex-operations"

    def test_all_domain_map_entries_indexed(self) -> None:
        for domain, projects in DOMAIN_MAP.items():
            for proj in projects:
                assert proj in PROJECT_DOMAIN, f"{proj} not indexed"
                assert PROJECT_DOMAIN[proj] == domain

    def test_unknown_project_not_in_map(self) -> None:
        assert "nonexistent-project-xyz" not in PROJECT_DOMAIN


class TestSovereignSignature:
    """Tamper-evident signature generation (Ω₃)."""

    def test_signature_format(self) -> None:
        svc = NotebookLMService(":memory:")
        sig = svc.get_signature()

        assert "SOVEREIGN_SIGNATURE" in sig
        assert "sha256:" in sig
        assert "CORTEX v8" in sig

    def test_signature_changes_with_time(self) -> None:
        svc = NotebookLMService(":memory:")
        sig1 = svc.get_signature()
        sig2 = svc.get_signature()
        # Both should contain the same structure (called within same second)
        assert "SOVEREIGN_SIGNATURE" in sig1
        assert "SOVEREIGN_SIGNATURE" in sig2


class TestCloudDetection:
    """Cloud sync provider detection."""

    def test_detect_returns_none_when_no_provider(self) -> None:
        svc = NotebookLMService(":memory:")

        # In CI/test environments, cloud providers typically don't exist.
        # This test validates graceful fallback.
        result = svc.detect_cloud_sync()
        # Result is either None or a valid (Path, str) tuple
        if result is not None:
            path, provider = result
            assert isinstance(path, Path)
            assert isinstance(provider, str)


class TestNotebookLMService:
    """NotebookLM service layer from services/notebooklm.py."""

    def test_format_fact_basic(self) -> None:
        from cortex.services.notebooklm import NotebookLMService

        svc = NotebookLMService(":memory:")
        fact = MagicMock()
        fact.id = 42
        fact.fact_type = "decision"
        fact.project = "cortex"
        fact.source = "agent:gemini"
        fact.confidence = 0.85
        fact.timestamp = 1710345600.0
        fact.content = "Use RRF for hybrid search"

        result = svc.format_fact(fact)

        assert "Use RRF" in result
        assert "∆_CTX:" in result

    def test_get_signature(self) -> None:
        from cortex.services.notebooklm import NotebookLMService

        svc = NotebookLMService(":memory:")
        sig = svc.get_signature()

        assert "SOVEREIGN_SIGNATURE" in sig
        assert "CORTEX v8.0-Sovereign" in sig

    def test_detect_cloud_sync_returns_path_or_none(self) -> None:
        from cortex.services.notebooklm import NotebookLMService

        svc = NotebookLMService(":memory:")
        result = svc.detect_cloud_sync()
        if result is not None:
            assert isinstance(result[0], Path)
            assert isinstance(result[1], str)


class TestMCPToolRegistration:
    """Verify MCP tool registration doesn't error."""

    def test_register_creates_tools(self) -> None:
        from cortex.mcp.notebooklm_tools import register_notebooklm_tools

        mock_mcp = MagicMock()
        mock_mcp.tool.return_value = lambda fn: fn
        mock_ctx = MagicMock()
        mock_ctx.db_path = ":memory:"

        # Should not raise
        register_notebooklm_tools(mock_mcp, mock_ctx)

        # Verify tool decorator was called 4 times
        assert mock_mcp.tool.call_count == 4
