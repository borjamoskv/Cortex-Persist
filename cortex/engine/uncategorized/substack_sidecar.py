import argparse
import logging
import sqlite3
from pathlib import Path

from cortex.services.email import send_reengagement_email

# Configuración de Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("CausalScheduler")

CORTEX_DB_PATH = Path("/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex_data.db")


def evaluate_retention(dry_run=True):
    """
    Escanea la base de datos local y evalúa el 'last_sign_in_at' o 'days_active'.
    Si un nodo de élite lleva inactivo > 15 días, dispara re-engagement.
    """
    logger.info("Iniciando Causal Scheduler (Evaluación de Retención)...")

    conn = sqlite3.connect(CORTEX_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Extraer Élite en riesgo (days_active > 15 y que sean import/music_media)
    cursor.execute("""
        SELECT email, name, days_active, opens, cluster 
        FROM audience 
        WHERE status = 'active' 
          AND days_active >= 15 
          AND cluster IN ('music_media', 'elite_individuals')
    """)

    risk_nodes = cursor.fetchall()

    logger.info(f"Nodos de Élite evaluados: {len(risk_nodes)} en riesgo inminente de Churn.")

    for node in risk_nodes:
        logger.info(
            f"[TAINT: RISK_OF_CHURN] {node['name']} ({node['email']}) - {node['days_active']} días sin actividad. Aperturas: {node['opens']}."
        )

        if not dry_run:
            # Aquí irá la integración de Mailgun / SMTP local
            logger.warning(f"DISPARANDO TRANSSACCIÓN A: {node['email']}")

            # Conexión resuelta a cortex.services.email
            send_reengagement_email(node["email"], node["cluster"])

            # Actualizar estado para no bombardear
            cursor.execute(
                "UPDATE audience SET status = 'churn_mitigated' WHERE email = ?", (node["email"],)
            )

    # Extraer Volumen puro (Para ataques de Reciprocidad Dirigida)
    cursor.execute("""
        SELECT count(*) as total FROM audience WHERE source = 'global_enriched'
    """)
    volume_total = cursor.fetchone()["total"]
    logger.info(f"Nodos de Volumen disponibles para Reciprocidad Dirigida: {volume_total}")

    if not dry_run:
        conn.commit()
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Substack Sidecar - Causal Retention Engine")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Desactiva el dry-run y ejecuta mutaciones de estado/envíos",
    )

    args = parser.parse_args()

    evaluate_retention(dry_run=not args.execute)
