"""Tests for MCP token-store validation and exergy accounting."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from mcp_saas.auth import deduct_exergy, verify_and_gate  # noqa: E402


def test_verify_and_gate_fails_closed_when_token_store_is_missing(tmp_path: Path) -> None:
    """Missing token stores must reject requests instead of accepting repo fixtures."""
    result = verify_and_gate("missing", token_path=tmp_path / "missing.yaml")
    assert result["valid"] is False
    assert result["error"] == "TOKEN_STORE_UNAVAILABLE"


def test_verify_and_gate_and_deduct_exergy_roundtrip(tmp_path: Path) -> None:
    """A valid token should authorize and debit exergy atomically."""
    token_store = tmp_path / "tokens.yaml"
    token_store.write_text(
        yaml.safe_dump(
            {
                "unit-test-token": {
                    "capabilities": ["intel", "foundry"],
                    "exergy_balance": "10.5",
                    "tenant_id": "tenant-alpha",
                }
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    authorized = verify_and_gate("unit-test-token", capability="intel", token_path=token_store)
    assert authorized["valid"] is True
    assert authorized["tenant_id"] == "tenant-alpha"
    assert authorized["balance"] == "10.5"

    remaining = deduct_exergy("unit-test-token", 2.5, token_path=token_store)
    assert remaining == "8.0"

    reloaded = yaml.safe_load(token_store.read_text(encoding="utf-8"))
    assert reloaded["unit-test-token"]["exergy_balance"] == "8.0"
