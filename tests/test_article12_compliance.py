import sys

import pytest

# Add core path
sys.path.append("/Users/borjafernandezangulo/Cortex-Persist/cortex-core")

from forensic_ledger import Article12Ledger
from article12_audit_api import Article12AuditAPI


@pytest.fixture
def article12_db(tmp_path):
    return tmp_path / "article12.db"


@pytest.fixture
def article12_secret_key():
    return "test-only-article12-ledger-key"


def test_ledger_record_and_verify(article12_db, article12_secret_key):
    ledger = Article12Ledger(db_path=article12_db, secret_key=article12_secret_key)

    # Record a test event
    tid = ledger.record_event(
        model_info={"name": "Test-Model", "v": "1.0"},
        input_text="Sample Input",
        output_text="Sample Output"
    )

    assert tid is not None

    # Verify integrity
    violations = ledger.verify_ledger_integrity()
    assert len(violations) == 0

def test_audit_report_generation(article12_db, article12_secret_key):
    ledger = Article12Ledger(db_path=article12_db, secret_key=article12_secret_key)
    ledger.record_event(
        model_info={"name": "Report-Test", "v": "1.0"},
        input_text="Report input",
        output_text="Report output",
    )

    api = Article12AuditAPI(db_path=article12_db, secret_key=article12_secret_key)
    report = api.get_conformity_report()

    assert report["regulation"] == "EU AI Act - Article 12 (Record-keeping)"
    assert "compliance_status" in report
    assert report["metrics"]["total_recorded_events"] > 0

def test_ledger_tamper_detection(article12_db, article12_secret_key):
    import sqlite3

    ledger = Article12Ledger(db_path=article12_db, secret_key=article12_secret_key)
    api = Article12AuditAPI(db_path=article12_db, secret_key=article12_secret_key)

    # Record event
    tid = ledger.record_event({"name": "Tamper-Test"}, "In", "Out")

    # Manually tamper with the DB (The "Regulator's Nightmare")
    conn = sqlite3.connect(article12_db)
    c = conn.cursor()
    c.execute("UPDATE compliance_logs SET output_fingerprint = 'TAMPERED' WHERE interaction_id = ?", (tid,))
    conn.commit()
    conn.close()

    # Verify that the violation is detected
    violations = ledger.verify_ledger_integrity()
    assert tid in violations

    report = api.get_conformity_report()
    assert report["compliance_status"] == "FAIL"

if __name__ == "__main__":
    # If run directly, execute with pytest
    pytest.main([__file__])
