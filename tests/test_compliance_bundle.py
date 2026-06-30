import os
import sqlite3
import json
import zipfile
import pytest
from pathlib import Path
from babylon60.audit.compliance_bundle import ComplianceBundler


@pytest.fixture
def mock_db_path(tmp_path):
    db_file = tmp_path / "test_ledger.db"

    # Setup mock schema and data
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE security_audit_log (
                audit_id TEXT PRIMARY KEY,
                timestamp TEXT,
                tenant_id TEXT,
                actor_role TEXT,
                actor_id TEXT,
                action TEXT,
                resource TEXT,
                status TEXT,
                prev_hash TEXT,
                signature TEXT,
                external_anchor TEXT
            )
        """)

        cursor.execute("""
            INSERT INTO security_audit_log VALUES (
                'audit-123', '2026-06-26T00:00:00Z', 'tenant-1', 'admin', 'actor-1',
                'CREATE', 'resource-1', 'SUCCESS', 'hash0', 'sig1',
                '{"rekor_uuid": "abc", "rfc3161_token": "def"}'
            )
        """)
        conn.commit()

    return str(db_file)


def test_compliance_bundle_export(mock_db_path, tmp_path):
    bundler = ComplianceBundler(db_path=mock_db_path)
    zip_path = tmp_path / "audit_bundle.zip"

    success = bundler.export_bundle(str(zip_path))
    assert success is True
    assert zip_path.exists()

    # Verify contents of zip
    with zipfile.ZipFile(zip_path, "r") as zipf:
        files = zipf.namelist()
        assert "metadata.json" in files
        assert "ledger_export.json" in files
        assert "signatures/record_000000_audit-123.json" in files

        # Check metadata
        metadata = json.loads(zipf.read("metadata.json"))
        assert metadata["format"] == "EU_AI_ACT_COMPLIANCE"
        assert metadata["total_records"] == 1

        # Check export data
        export_data = json.loads(zipf.read("ledger_export.json"))
        assert len(export_data) == 1
        assert export_data[0]["audit_id"] == "audit-123"
        assert export_data[0]["external_anchor"]["rekor_uuid"] == "abc"
