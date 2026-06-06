import sqlite3
import sys

DB_PATH = "influencer_audit_v1.db"


class ContradictionTracker:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    def log_contradiction(self, axioma: str, accion: str, evidencia_url: str):
        """
        [C5-REAL] Registra una disonancia discursiva en contradicciones_documentadas.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO contradicciones_documentadas (axioma_filosofico_declarado, accion_real_documentada, evidencia_url)
                VALUES (?, ?, ?)
            """,
                (axioma, accion, evidencia_url),
            )
            conn.commit()
            print("[C5-REAL] Contradicción registrada con éxito en el Ledger.")
        except Exception as e:
            print(f"[ERROR] Fallo al escribir contradicción: {e}")
        finally:
            conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(
            "Usage: python contradiction_tracker.py <axioma_declarado> <accion_documentada> <evidencia_url>"
        )
        sys.exit(1)

    axioma = sys.argv[1]
    accion = sys.argv[2]
    url = sys.argv[3]

    tracker = ContradictionTracker()
    tracker.log_contradiction(axioma, accion, url)
