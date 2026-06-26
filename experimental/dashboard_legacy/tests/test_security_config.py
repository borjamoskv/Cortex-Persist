"""Unit tests for runtime security configuration."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from security_config import (  # noqa: E402
    SecurityConfigurationError,
    resolve_api_key,
    resolve_token_store_path,
)


def test_resolve_api_key_requires_env_in_production() -> None:
    """Production must refuse checked-in or missing API keys."""
    with pytest.raises(SecurityConfigurationError):
        resolve_api_key({"server": {"env": "production", "api_key": None}}, environ={})


def test_resolve_api_key_allows_non_genesis_config_in_development() -> None:
    """Development can use an explicit non-genesis config secret."""
    secret = resolve_api_key(
        {"server": {"env": "development", "api_key": "dev-only-secret"}},
        environ={},
    )
    assert secret == "dev-only-secret"


def test_resolve_token_store_path_prefers_env_override(tmp_path: Path) -> None:
    """Runtime token stores should come from env overrides when provided."""
    token_store = tmp_path / "tokens.yaml"
    resolved = resolve_token_store_path({"CORTEX_MCP_TOKENS_FILE": str(token_store)})
    assert resolved == token_store
