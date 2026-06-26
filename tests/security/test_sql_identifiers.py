# [C5-REAL] Exergy-Maximized
import pytest

from cortex.utils.sql_identifiers import (
    is_safe_identifier,
    quote_identifier,
    validate_sql_identifier,
)


def test_valid_identifiers():
    valid = [
        "users",
        "facts_meta",
        "vec_facts_tenant1_proj2",
        "s0",
        "idx_void_mih_s15",
        "_",
        "A",
        "a1",
        "a" * 64,
    ]
    for identifier in valid:
        assert validate_sql_identifier(identifier) == identifier
        assert is_safe_identifier(identifier) is True


def test_invalid_identifiers():
    invalid = [
        "",
        " ",
        "users table",
        "users; DROP TABLE facts_meta",
        "1facts_meta",
        "facts-meta",
        "tenant$id",
        "a" * 65,
        "users\n",
        "users\0",
    ]
    for identifier in invalid:
        with pytest.raises(ValueError):
            validate_sql_identifier(identifier)
        assert is_safe_identifier(identifier) is False


def test_quote_identifier():
    assert quote_identifier("users") == '"users"'
    with pytest.raises(ValueError):
        quote_identifier("users; DROP TABLE facts_meta")


def test_schema_trait_get_domain_tables_rejection():
    from unittest.mock import MagicMock
    from cortex.memory.traits.schema import SchemaTrait

    class DummySchema(SchemaTrait):
        def __init__(self):
            pass

    ds = DummySchema()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.fetchone.return_value = ("some_table",)

    with pytest.raises(ValueError, match="Unsafe or empty tenant/project ID rejected"):
        ds._get_domain_tables(mock_conn, "", "proj")
    with pytest.raises(ValueError, match="Unsafe or empty tenant/project ID rejected"):
        ds._get_domain_tables(mock_conn, "tenant", "")
    with pytest.raises(ValueError, match="Unsafe or empty tenant/project ID rejected"):
        ds._get_domain_tables(mock_conn, "@", "proj")


def test_task_queue_update_rejection(tmp_path):
    from cortex_extensions.aether.queue import TaskQueue

    db_file = tmp_path / "aether.db"
    queue = TaskQueue(db_file)
    with pytest.raises(ValueError):
        queue.update("task_123", **{"status; DROP TABLE agent_tasks; --": "pending"})
    with pytest.raises(ValueError, match="Unauthorized field update rejected"):
        queue.update("task_123", **{"invalid_field_name": "value"})


def test_ledger_store_ensure_compat_columns_rejection():
    from cortex.ledger.store import LedgerStore

    store = LedgerStore(db_path=":memory:")
    with pytest.raises(ValueError):
        store._ensure_compat_columns(None, "invalid; DROP TABLE enrichment_jobs; --")
