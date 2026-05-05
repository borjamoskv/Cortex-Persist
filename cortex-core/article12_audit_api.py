import json
import sqlite3
import hashlib
from forensic_ledger import Article12Ledger, COMPLIANCE_DB

class Article12AuditAPI:
    """
    Forensic Audit Interface — EU AI Act Article 12 Infrastructure.
    Provides a secure gateway for regulatory review of AI event logs.
    """

    def __init__(self, db_path=None, secret_key=None):
        self.ledger = Article12Ledger(db_path=db_path, secret_key=secret_key)
        self.db_path = self.ledger.db_path

    def get_conformity_report(self):
        """
        Generates a summary report of the current compliance state.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM compliance_logs")
        total_events = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM compliance_logs WHERE human_oversight_trigger = 1")
        human_interventions = c.fetchone()[0]

        conn.close()

        violations = self.ledger.verify_ledger_integrity()

        report = {
            "regulation": "EU AI Act - Article 12 (Record-keeping)",
            "compliance_status": "PASS" if not violations else "FAIL",
            "metrics": {
                "total_recorded_events": total_events,
                "human_oversight_events": human_interventions,
                "integrity_violations": len(violations)
            },
            "system_integrity_hash": self._generate_ledger_hash()
        }

        return report

    def export_logs_json(self):
        """
        Exports the entire ledger in a standardized JSON format for regulators.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM compliance_logs")
        rows = c.fetchall()
        conn.close()

        logs = []
        for row in rows:
            logs.append({
                "interaction_id": row[0],
                "timestamp": row[1],
                "model": json.loads(row[2]) if row[2].startswith("{") else row[2],
                "in_proof": row[3],
                "out_proof": row[4],
                "human": bool(row[5]),
                "seal": row[6]
            })

        return logs

    def verify_interaction_claim(self, interaction_id, claimed_input, claimed_output):
        """
        Audit verification: Checks if a claimed interaction matches the ZK-Semantic Proof.
        Returns (is_valid, input_similarity, output_similarity).
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT input_fingerprint, output_fingerprint FROM compliance_logs WHERE interaction_id = ?", (interaction_id,))
        row = c.fetchone()
        conn.close()

        if not row:
            return False, 0, 0

        in_proof, out_proof = row
        in_match, in_sim = self.ledger.zk.verify_proof(claimed_input, in_proof)
        out_match, out_sim = self.ledger.zk.verify_proof(claimed_output, out_proof)

        return (in_match and out_match), in_sim, out_sim

    def _generate_ledger_hash(self):
        """
        Generates a master hash of the entire ledger to anchor the state.
        """
        logs = self.export_logs_json()
        log_str = json.dumps(logs, sort_keys=True)
        return hashlib.sha256(log_str.encode()).hexdigest()

if __name__ == "__main__":
    api = Article12AuditAPI()
    print("📋 [CORTEX AUDIT] Generating Article 12 Conformity Report...")
    report = api.get_conformity_report()
    print(json.dumps(report, indent=2))

    if report["compliance_status"] == "PASS":
        print("\n✅ System matches Article 12 infrastructure requirements.")
        print(f"🔗 Master Ledger Hash: {report['system_integrity_hash']}")
    else:
        print("\n❌ CRITICAL: Ledger integrity compromised. Forensic audit required.")
