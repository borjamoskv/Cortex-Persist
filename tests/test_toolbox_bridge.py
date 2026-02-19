"""Tests for CORTEX MCP Toolbox Bridge.

Tests bridge configuration, URL validation, and MCPGuard extensions
without requiring a running Toolbox server.
"""

import pytest

from cortex.mcp.guard import MCPGuard
from cortex.mcp.toolbox_bridge import ToolboxBridge, ToolboxConfig


class TestToolboxConfig:
    """Test ToolboxConfig dataclass."""

    def test_default_config(self):
        """Default config should use localhost:5000."""
        cfg = ToolboxConfig()
        assert cfg.server_url == "http://127.0.0.1:5000"
        assert cfg.timeout_seconds == 30.0
        assert cfg.toolset == ""
        assert len(cfg.allowed_server_urls) >= 2

    def test_custom_config(self):
        """Custom config should override defaults."""
        cfg = ToolboxConfig(
            server_url="http://custom:8080",
            toolset="my-tools",
            timeout_seconds=60.0,
        )
        assert cfg.server_url == "http://custom:8080"
        assert cfg.toolset == "my-tools"
        assert cfg.timeout_seconds == 60.0

    def test_from_env(self, monkeypatch):
        """Config should read from environment variables."""
        monkeypatch.setenv("TOOLBOX_URL", "http://env-host:9090")
        monkeypatch.setenv("TOOLBOX_TOOLSET", "cortex-readonly")
        monkeypatch.setenv("TOOLBOX_TIMEOUT", "45")

        cfg = ToolboxConfig.from_env()
        assert cfg.server_url == "http://env-host:9090"
        assert cfg.toolset == "cortex-readonly"
        assert cfg.timeout_seconds == 45.0


class TestToolboxBridge:
    """Test ToolboxBridge initialization and configuration."""

    def test_bridge_creation(self):
        """Bridge should be creatable with default config."""
        bridge = ToolboxBridge()
        assert bridge.config.server_url == "http://127.0.0.1:5000"
        assert bridge._client is None
        assert bridge._tools == []

    def test_bridge_with_custom_config(self):
        """Bridge should accept custom config."""
        cfg = ToolboxConfig(server_url="http://my-server:5000")
        bridge = ToolboxBridge(config=cfg)
        assert bridge.config.server_url == "http://my-server:5000"

    def test_bridge_repr(self):
        """Repr should show connection status."""
        bridge = ToolboxBridge()
        r = repr(bridge)
        assert "disconnected" in r
        assert "tools=0" in r

    def test_bridge_is_available_flag(self):
        """is_available should reflect SDK installation."""
        bridge = ToolboxBridge()
        assert isinstance(bridge.is_available, bool)

    def test_bridge_tool_names_empty(self):
        """tool_names should be empty before connection."""
        bridge = ToolboxBridge()
        assert bridge.tool_names == []

    def test_bridge_tools_empty(self):
        """tools should be empty before connection."""
        bridge = ToolboxBridge()
        assert bridge.tools == []

    def test_invalid_server_url_rejected(self):
        """Non-allowlisted URLs should be rejected."""
        cfg = ToolboxConfig(
            server_url="http://evil-server:5000",
            allowed_server_urls=["http://127.0.0.1:5000"],
        )
        bridge = ToolboxBridge(config=cfg)
        with pytest.raises(ValueError, match="not in the allowlist"):
            bridge._validate_server_url()

    def test_valid_server_url_accepted(self):
        """Allowlisted URLs should pass validation."""
        cfg = ToolboxConfig(
            server_url="http://127.0.0.1:5000",
            allowed_server_urls=["http://127.0.0.1:5000"],
        )
        bridge = ToolboxBridge(config=cfg)
        bridge._validate_server_url()  # Should not raise


class TestMCPGuardExternalQuery:
    """Test MCPGuard extensions for external queries."""

    def test_validate_empty_tool_name_rejected(self):
        """Empty tool names should be rejected."""
        with pytest.raises(ValueError, match="tool name cannot be empty"):
            MCPGuard.validate_external_query("", {"key": "value"})

    def test_validate_long_tool_name_rejected(self):
        """Excessively long tool names should be rejected."""
        with pytest.raises(ValueError, match="tool name too long"):
            MCPGuard.validate_external_query("x" * 300, {"key": "value"})

    def test_valid_external_query(self):
        """Normal external queries should pass validation."""
        MCPGuard.validate_external_query("search-facts", {"query": "hello"})

    def test_poisoning_in_params_rejected(self):
        """Data poisoning in parameter values should be caught."""
        with pytest.raises(ValueError, match="suspicious pattern"):
            MCPGuard.validate_external_query(
                "my-tool",
                {"query": "; DROP TABLE facts; --"},
            )

    def test_clean_params_accepted(self):
        """Clean parameter values should pass."""
        MCPGuard.validate_external_query(
            "search-facts",
            {"query": "CORTEX memory architecture", "limit": "10"},
        )

    def test_validate_toolbox_url_allowed(self):
        """Allowed URLs should pass validation."""
        MCPGuard.validate_toolbox_url("http://127.0.0.1:5000")
        MCPGuard.validate_toolbox_url("http://localhost:5000")

    def test_validate_toolbox_url_rejected(self):
        """Non-allowed URLs should be rejected."""
        with pytest.raises(ValueError, match="not in allowlist"):
            MCPGuard.validate_toolbox_url("http://evil-server:5000")

    def test_add_allowed_toolbox_url(self):
        """Should be able to add URLs to the allowlist."""
        test_url = "http://test-toolbox:9090"
        MCPGuard.add_allowed_toolbox_url(test_url)
        # Should now pass validation
        MCPGuard.validate_toolbox_url(test_url)
        # Cleanup
        MCPGuard._ALLOWED_TOOLBOX_URLS.remove(test_url.rstrip("/"))

    def test_trailing_slash_normalized(self):
        """URLs with trailing slashes should be normalized."""
        MCPGuard.validate_toolbox_url("http://127.0.0.1:5000/")
