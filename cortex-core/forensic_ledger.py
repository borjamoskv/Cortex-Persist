import json
import time
import sqlite3
import hashlib
import hmac
import os
import uuid
from pathlib import Path
from cortex_zk_masking import ZKSemanticMasking

COMPLIANCE_DB = "/Users/borjafernandezangulo/Cortex-Persist/cortex-core/cortex_compliance_article12.db"
SECRET_KEY_ENV = "CORTEX_ARTICLE12_LEDGER_KEY"


def _resolve_secret_key(secret_key=None):
    if secret_key is None:
        secret_key = os.environ.get(SECRET_KEY_ENV)
    if secret_key is None:
        raise RuntimeError(f"{SECRET_KEY_ENV} is required for Article 12 ledger sealing")
    if isinstance(secret_key, str):
        return secret_key.encode("utf-8")
    return secret_key

class Article12Ledger:
    """
    Sovereign Traceability Ledger — EU AI Act Article 12 Infrastructure.
    Ensures automatic recording of events with cryptographic integrity.
    """

    def __init__(self, db_path=None, secret_key=None):
        self.db_path = str(Path(db_path or COMPLIANCE_DB))
        self._secret_key = _resolve_secret_key(secret_key)
        self._init_db()
        self.zk = ZKSemanticMasking() # Sovereign ZK Layer

    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS compliance_logs (
                interaction_id TEXT PRIMARY KEY,
                timestamp TEXT,
                model_info TEXT,
                input_fingerprint TEXT,
                output_fingerprint TEXT,
                human_oversight_trigger INTEGER,
                integrity_seal TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def record_event(self, model_info, input_text, output_text, human_triggered=0):
        """
        Records an AI interaction event with Article 12 compliance metadata using ZK-Semantic Proofs.
        """
        interaction_id = str(uuid.uuid4())
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Article 12 + GDPR: ZK-Semantic Fingerprints
        input_fingerprint = self.zk.generate_proof(input_text)
        output_fingerprint = self.zk.generate_proof(output_text)

        # Create the record object for sealing
        record_body = {
            "id": interaction_id,
            "ts": timestamp,
            "model": model_info,
            "in": input_fingerprint,
            "out": output_fingerprint,
            "human": human_triggered
        }

        # Generate Integrity Seal (HMAC-SHA256)
        seal = hmac.new(
            self._secret_key,
            json.dumps(record_body, sort_keys=True).encode(),
            hashlib.sha256,
        ).hexdigest()

        # Persist to C5-REAL Ledger
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            INSERT INTO compliance_logs
            (interaction_id, timestamp, model_info, input_fingerprint, output_fingerprint, human_oversight_trigger, integrity_seal)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (interaction_id, timestamp, json.dumps(model_info), input_fingerprint, output_fingerprint, human_triggered, seal))
        conn.commit()
        conn.close()

        return interaction_id

    def verify_ledger_integrity(self):
        """
        Walks the ledger and verifies that all seals are valid.
        This is the basis for the Forensic Audit.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM compliance_logs ORDER BY interaction_id")
        rows = c.fetchall()
        conn.close()

        violations = []
        for row in rows:
            interaction_id, ts, model, in_fp, out_fp, human, seal = row
            try:
                model_data = json.loads(model)
            except json.JSONDecodeError:
                model_data = model

            record_body = {
                "id": interaction_id,
                "ts": ts,
                "model": model_data,
                "in": in_fp,
                "out": out_fp,
                "human": human
            }
            expected_seal = hmac.new(
                self._secret_key,
                json.dumps(record_body, sort_keys=True).encode(),
                hashlib.sha256,
            ).hexdigest()
            if seal != expected_seal:
                violations.append(interaction_id)

        return violations

if __name__ == "__main__":
    ledger = Article12Ledger()
    print("🚀 Initializing Article 12 Compliance Infrastructure...")
    tid = ledger.record_event({"name": "Gemini-3-Flash", "version": "1.0"}, "Hello CORTEX", "Hello Borja. Article 12 active.")
    print(f"✅ Event recorded: {tid}")

    violations = ledger.verify_ledger_integrity()
    if not violations:
        print("🛡️ Ledger Integrity: VERIFIED (C5-REAL)")
    else:
        print(f"⚠️ Integrity Violation detected in interactions: {violations}")
