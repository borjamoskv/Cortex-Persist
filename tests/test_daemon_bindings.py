from __future__ import annotations

from cortex.engine import reporterd
from cortex.extensions.daemon import ccr_proxy


def test_reporterd_binds_to_loopback_by_default(monkeypatch) -> None:
    monkeypatch.delenv("CORTEX_REPORTERD_HOST", raising=False)

    assert reporterd._get_bind_host() == "127.0.0.1"


def test_reporterd_bind_host_allows_override(monkeypatch) -> None:
    monkeypatch.setenv("CORTEX_REPORTERD_HOST", "0.0.0.0")

    assert reporterd._get_bind_host() == "0.0.0.0"


def test_ccr_proxy_binds_to_loopback_by_default(monkeypatch) -> None:
    monkeypatch.delenv("CCR_BIND_HOST", raising=False)

    assert ccr_proxy._get_bind_host() == "127.0.0.1"


def test_ccr_proxy_bind_host_allows_override(monkeypatch) -> None:
    monkeypatch.setenv("CCR_BIND_HOST", "0.0.0.0")

    assert ccr_proxy._get_bind_host() == "0.0.0.0"
