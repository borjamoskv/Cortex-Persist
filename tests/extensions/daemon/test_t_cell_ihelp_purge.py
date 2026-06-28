# [C5-REAL] Exergy-Maximized
import pytest
import re
from cortex.engine.causal.taint_engine import MHCAntigenRouter
from cortex.extensions.daemon.t_cell_ihelp_purge import IHelpPurgeDaemon
from cortex.routes.telemetry import BASE_MAFIA_NODES


def test_t_cell_ihelp_purge_signature_construction():
    """
    Verifies that the daemon dynamically loads BASE_MAFIA_NODES, escapes all regex
    characters, replaces whitespace with \\s+, and builds the correct regex.
    """
    router = MHCAntigenRouter()
    daemon = IHelpPurgeDaemon(router)

    # Check that signature matches the expected format
    assert daemon.antigen_signature.startswith("(?i)\\b(")
    assert daemon.antigen_signature.endswith(")\\b")

    # Check key nodes are in the signature pattern
    for node in BASE_MAFIA_NODES:
        escaped = re.escape(node)
        cleaned = re.sub(r'(\\ )|\s+', r'\\s+', escaped)
        assert cleaned in daemon.antigen_signature


def test_t_cell_ihelp_purge_routing():
    """
    Verifies that various payloads with mafia nodes are routed correctly,
    while safe payloads are not.
    """
    router = MHCAntigenRouter()
    daemon = IHelpPurgeDaemon(router)

    # Trigger with exact nodes
    assert router.present_antigen("david dominguez is editing a newsletter") == daemon.agent_id
    assert router.present_antigen("Go to cosasdefreelance.com and read it") == daemon.agent_id
    assert router.present_antigen("I need botondeayuda.com now") == daemon.agent_id
    assert router.present_antigen("This is ihelp project") == daemon.agent_id

    # Case insensitivity
    assert router.present_antigen("David Dominguez") == daemon.agent_id
    assert router.present_antigen("IHELP") == daemon.agent_id

    # Whitespace variations (\s+)
    assert router.present_antigen("david \t dominguez") == daemon.agent_id
    assert router.present_antigen("david \n dominguez") == daemon.agent_id

    # Safe payload not matching any antigen
    assert router.present_antigen("This is a clean payload talking about rust development.") is None


@pytest.mark.asyncio
async def test_t_cell_ihelp_purge_phagocytize(monkeypatch, tmp_path):
    """
    Verifies that the phagocytize method correctly calculates saved bytes/tokens
    and returns a valid C5-REAL audit trail.
    """
    db_file = tmp_path / "cortex_test.db"
    monkeypatch.setenv("CORTEX_DB_PATH", str(db_file))

    router = MHCAntigenRouter()
    daemon = IHelpPurgeDaemon(router)

    payload = "Anergy injection from david dominguez for ihelp."
    source = "test-agent"

    audit_trail = await daemon.phagocytize(payload, source)

    # Check structure
    assert audit_trail["action"] == "PHAGOCYTOSIS"
    assert audit_trail["antigen_type"] == "SUBSTACK_MAFIA_IHELP"
    assert audit_trail["source_agent"] == source
    assert "timestamp" in audit_trail
    assert "hash_destroyed" in audit_trail

    # Verify metrics
    expected_bytes = len(payload.encode("utf-8").strip())  # canonicalized content length
    expected_tokens = expected_bytes // 3
    assert audit_trail["exergy_metrics"]["bytes_saved"] == expected_bytes
    assert audit_trail["exergy_metrics"]["tokens_saved"] == expected_tokens


@pytest.mark.asyncio
async def test_t_cell_ihelp_purge_scan_telemetry_targets(monkeypatch, tmp_path):
    """
    Verifies scan_telemetry_targets executes concurrent checkouts, triggers phagocytosis,
    logs anomalies, and persists everything in the Master Ledger.
    """
    import asyncio
    from unittest.mock import AsyncMock, patch, MagicMock
    import httpx
    from cortex.database.core import connect_async

    db_file = tmp_path / "cortex_test_scan.db"
    monkeypatch.setenv("CORTEX_DB_PATH", str(db_file))

    router = MHCAntigenRouter()
    daemon = IHelpPurgeDaemon(router)

    # Mock getaddrinfo
    # We want DNS to succeed for some, but fail for one to trigger FORENSIC_ANOMALY
    async def mock_getaddrinfo(host, port, *args, **kwargs):
        if "emarketersocial.com" in host:
            raise OSError("DNS lookup failed")
        return [(2, 1, 6, "", ("127.0.0.1", port or 0))]

    # Mock HTTP client
    async def mock_get(url, *args, **kwargs):
        # Trigger phagocytosis on one domain
        if "daviddominguez.substack.com/feed" in url:
            return AsyncMock(status_code=200, text="Alert: david dominguez has posted")
        # Trigger HTTP connection failure on another domain
        if "masteryweeks.com" in url:
            raise httpx.ConnectError("Connection timed out")
        return AsyncMock(status_code=200, text="safe content")

    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=mock_get)
    mock_client.aclose = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    # Patch getaddrinfo on the loop
    loop = asyncio.get_running_loop()
    with patch.object(loop, "getaddrinfo", new=mock_getaddrinfo), \
         patch("httpx.AsyncClient", return_value=mock_client):
        res = await daemon.scan_telemetry_targets()

    assert res["status"] == "completed"
    assert res["checked_domains"] > 0

    # Let's inspect the database to make sure actions were written
    conn = await connect_async(str(db_file))
    try:
        async with conn.execute("SELECT action, resource, status FROM security_audit_log ORDER BY rowid ASC") as c:
            rows = await c.fetchall()
    finally:
        await conn.close()

    actions = [r[0] for r in rows]
    # Check that we logged FORENSIC_ANOMALY (from DNS failure or HTTP failure) and PHAGOCYTOSIS (from matched content)
    assert "FORENSIC_ANOMALY" in actions
    assert "PHAGOCYTOSIS" in actions
