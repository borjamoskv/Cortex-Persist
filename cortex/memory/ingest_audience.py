import argparse
import csv
import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Configuración de Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Rutas
CORTEX_DB_PATH = Path("/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex_data.db")
if not CORTEX_DB_PATH.parent.exists():
    CORTEX_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def init_db():
    """Inicializa la base de datos local emulando el modelo CRM transaccional (tipo Supabase)."""
    conn = sqlite3.connect(CORTEX_DB_PATH)
    cursor = conn.cursor()

    # Tabla de Audiencia
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audience (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        name TEXT,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_sign_in_at TIMESTAMP,
        opens INTEGER DEFAULT 0,
        clicks INTEGER DEFAULT 0,
        days_active INTEGER DEFAULT 0,
        source TEXT,
        cluster TEXT,
        raw_user_meta_data TEXT,
        taint_hash TEXT
    )
    """)
    conn.commit()
    conn.close()
    logger.info("Base de datos de audiencia inicializada.")


def _generate_taint_hash(email: str, timestamp: str) -> str:
    """Genera un Taint Hash (AX-044) para la trazabilidad de CORTEX."""
    raw = f"taint:{email}:{timestamp}"
    return hashlib.sha3_256(raw.encode()).hexdigest()


def ingest_active_subscribers(csv_path: str):
    """Ingesta la cohorte Élite (Métricas completas)."""
    conn = sqlite3.connect(CORTEX_DB_PATH)
    cursor = conn.cursor()

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            email = row.get("email", "").strip()
            if not email:
                continue

            name = row.get("name", "")
            opens = int(row.get("opens", 0))
            clicks = int(row.get("clicks", 0))
            days_active = int(row.get("daysActive", 0))
            source = row.get("source", "")
            cluster = row.get("cluster", "")
            verdict = row.get("verdict", "")

            # Simulando last_sign_in_at en base a daysActive (Si lleva 20 días activo, la última vez fue ayer)
            # Esto es una aproximación heurística si no hay timestamp real. Asumimos que si tiene aperturas, interactuó recientemente.
            last_sign_in_at = (
                (datetime.now() - timedelta(days=1)).isoformat() if opens > 0 else None
            )
            created_at = (datetime.now() - timedelta(days=days_active)).isoformat()
            taint = _generate_taint_hash(email, created_at)

            raw_meta = json.dumps({"verdict": verdict})

            try:
                cursor.execute(
                    """
                INSERT INTO audience 
                (email, name, created_at, last_sign_in_at, opens, clicks, days_active, source, cluster, raw_user_meta_data, taint_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(email) DO UPDATE SET
                    opens=excluded.opens,
                    clicks=excluded.clicks,
                    days_active=excluded.days_active,
                    last_sign_in_at=excluded.last_sign_in_at,
                    cluster=excluded.cluster,
                    raw_user_meta_data=excluded.raw_user_meta_data
                """,
                    (
                        email,
                        name,
                        created_at,
                        last_sign_in_at,
                        opens,
                        clicks,
                        days_active,
                        source,
                        cluster,
                        raw_meta,
                        taint,
                    ),
                )
                count += 1
            except sqlite3.Error as e:
                logger.error(f"Error ingestando {email}: {e}")

    conn.commit()
    conn.close()
    logger.info(f"Ingestada cohorte Élite: {count} registros (C5-REAL).")


def ingest_global_enriched(csv_path: str):
    """Ingesta la base de volumen."""
    conn = sqlite3.connect(CORTEX_DB_PATH)
    cursor = conn.cursor()

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            email = row.get("Email", "").strip()
            if not email:
                continue

            name = row.get("Author", "")
            subdomain = row.get("Subdomain", "")
            source_url = row.get("Source_URL", "")

            created_at = datetime.now().isoformat()
            taint = _generate_taint_hash(email, created_at)
            raw_meta = json.dumps(
                {"subdomain": subdomain, "source_url": source_url, "target_type": "volume"}
            )

            try:
                cursor.execute(
                    """
                INSERT INTO audience 
                (email, name, created_at, source, cluster, raw_user_meta_data, taint_hash)
                VALUES (?, ?, ?, 'global_enriched', 'volume', ?, ?)
                ON CONFLICT(email) DO NOTHING
                """,
                    (email, name, created_at, raw_meta, taint),
                )

                if cursor.rowcount > 0:
                    count += 1
            except sqlite3.Error as e:
                logger.error(f"Error ingestando volumen {email}: {e}")

    conn.commit()
    conn.close()
    logger.info(f"Ingestada base de Volumen: {count} nuevos registros.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingesta Soberana de Audiencia para CORTEX-Sidecar"
    )
    parser.add_argument("--elite", type=str, help="Path al CSV de suscriptores activos (Élite)")
    parser.add_argument("--volume", type=str, help="Path al CSV de volumen enriquecido")

    args = parser.parse_args()

    init_db()

    if args.elite:
        ingest_active_subscribers(args.elite)
    if args.volume:
        ingest_global_enriched(args.volume)

    if not args.elite and not args.volume:
        logger.warning("No se proporcionaron archivos CSV. Ejecutando solo inicialización DB.")
