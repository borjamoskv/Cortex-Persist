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


def test_t_cell_ihelp_purge_phagocytize():
    """
    Verifies that the phagocytize method correctly calculates saved bytes/tokens
    and returns a valid C5-REAL audit trail.
    """
    router = MHCAntigenRouter()
    daemon = IHelpPurgeDaemon(router)

    payload = "Anergy injection from david dominguez for ihelp."
    source = "test-agent"

    audit_trail = daemon.phagocytize(payload, source)

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
