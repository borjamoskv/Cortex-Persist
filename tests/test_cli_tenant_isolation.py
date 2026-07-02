# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import json
import os
import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from babylon60.cli import cli
from babylon60.cli.common import resolve_cli_tenant
from babylon60.extensions.security.tenant import tenant_id_var


def test_resolve_cli_tenant_explicit():
    # Explicit tenant should override everything and set context
    resolve_cli_tenant("tenant-explicit")
    assert tenant_id_var.get() == "tenant-explicit"


def test_resolve_cli_tenant_from_env(monkeypatch):
    monkeypatch.setenv("CORTEX_TENANT_ID", "tenant-from-env")
    resolve_cli_tenant("default")
    assert tenant_id_var.get() == "tenant-from-env"


def test_resolve_cli_tenant_from_active_context(monkeypatch, tmp_path):
    # Mock active-context.json path inside resolve_cli_tenant
    config_file = tmp_path / "active-context.json"
    config_file.write_text(json.dumps({"tenant_id": "tenant-from-config"}), encoding="utf-8")

    # Clear CORTEX_TENANT_ID from environment
    monkeypatch.delenv("CORTEX_TENANT_ID", raising=False)

    with (
        patch("pathlib.Path.is_file", return_value=True),
        patch(
            "pathlib.Path.read_text", return_value=json.dumps({"tenant_id": "tenant-from-config"})
        ),
    ):
        resolve_cli_tenant("default")
        assert tenant_id_var.get() == "tenant-from-config"


def test_resolve_cli_tenant_fallback(monkeypatch):
    monkeypatch.delenv("CORTEX_TENANT_ID", raising=False)
    with patch("pathlib.Path.is_file", return_value=False):
        resolve_cli_tenant("default")
        assert tenant_id_var.get() == "default"
