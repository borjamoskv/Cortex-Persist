import argparse
import csv
import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Logging Configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Paths
CORTEX_DB_PATH = Path("~/10_PROJECTS/cortex-persist/cortex_data.db")
if not CORTEX_DB_PATH.parent.exists():
    CORTEX_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def init_db():
    """Initializes the local database emulating the transactional CRM model (Supabase type)."""
    conn = sqlite3.connect(CORTEX_DB_PATH)
    cursor = conn.cursor()

    # Audience Table
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
    logger.info("Audience database initialized.")


def _generate_taint_hash(email: str, timestamp: str) -> str:
    """Generates a Taint Hash (AX-044) for CORTEX traceability."""
    raw = f"taint:{email}:{timestamp}"
    return hashlib.sha3_256(raw.encode()).hexdigest()


def ingest_active_subscribers(csv_path: str):
    """Ingests the Elite cohort (Full metrics)."""
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

            # Simulating last_sign_in_at based on daysActive (If active for 20 days, the last time was yesterday)
            # This is a heuristic approximation if there is no real timestamp. We assume that if it has opens, it interacted recently.
            last_sign_in_at = (
                (datetime.now() - timedelta(days=1)).isoformat() if opens > 0 else None
            )
            created_at = (datetime.now() - timedelta(days=days_active)).isoformat()
            taint = _generate_taint_hash(email, created_at)

            raw_meta = json.dumps({"verdict": verdict})

            try:
                cursor.execute(  # bypass-tenant
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
                logger.error(f"Error ingesting {email}: {e}")

    conn.commit()
    conn.close()
    logger.info(f"Elite cohort ingested: {count} records (C5-REAL).")


def ingest_global_enriched(csv_path: str):
    """Ingests the volume base."""
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
                cursor.execute(  # bypass-tenant
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
                logger.error(f"Error ingesting volume {email}: {e}")

    conn.commit()
    conn.close()
    logger.info(f"Volume base ingested: {count} new records.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sovereign Audience Ingestion for CORTEX-Sidecar"
    )
    parser.add_argument("--elite", type=str, help="Path to the active subscribers CSV (Elite)")
    parser.add_argument("--volume", type=str, help="Path to the enriched volume CSV")

    args = parser.parse_args()

    init_db()

    if args.elite:
        ingest_active_subscribers(args.elite)
    if args.volume:
        ingest_global_enriched(args.volume)

    if not args.elite and not args.volume:
        logger.warning("No CSV files provided. Executing only DB initialization.")
