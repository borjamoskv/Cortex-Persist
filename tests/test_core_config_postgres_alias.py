from __future__ import annotations

from cortex.core.config import CortexConfig


def test_config_pg_url_accepts_postgres_dsn_alias(monkeypatch) -> None:
    monkeypatch.delenv("CORTEX_PG_URL", raising=False)
    monkeypatch.setenv("POSTGRES_DSN", "postgresql://alias-dsn")
    cfg = CortexConfig.from_env()
    assert cfg.PG_URL == "postgresql://alias-dsn"
