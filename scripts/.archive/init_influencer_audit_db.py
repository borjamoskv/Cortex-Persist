import sqlite3

DB_PATH = "influencer_audit_v1.db"


def init_db():
    print(f"[C5-REAL] Initializing relational schema at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Catálogo de Contenido (Vídeos_Fuente)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS videos_fuente (
        video_id TEXT PRIMARY KEY,
        creador_id TEXT NOT NULL,
        fecha_publicacion DATETIME,
        url_archivada TEXT,
        duracion_total INTEGER
    )
    """)

    # 2. El Espectáculo de la Humillación (Eventos_Acoso)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS eventos_acoso (
        acoso_id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id TEXT NOT NULL,
        timestamp_inicio_fin TEXT,
        target_id TEXT,
        taxonomia_ataque TEXT,
        cita_textual_exacta TEXT,
        FOREIGN KEY(video_id) REFERENCES videos_fuente(video_id)
    )
    """)

    # 3. La Figura Prohibida y la Monetización (Eventos_Victimismo)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS eventos_victimismo (
        victim_id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id TEXT NOT NULL,
        evidencia_externa_instrumentalizada TEXT,
        tono_reclamo TEXT,
        call_to_action_economica BOOLEAN,
        FOREIGN KEY(video_id) REFERENCES videos_fuente(video_id)
    )
    """)

    # 4. Disonancia Discursiva (Contradicciones_Documentadas)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contradicciones_documentadas (
        contra_id INTEGER PRIMARY KEY AUTOINCREMENT,
        axioma_filosofico_declarado TEXT,
        accion_real_documentada TEXT,
        evidencia_url TEXT
    )
    """)

    conn.commit()
    conn.close()
    print("[C5-REAL] Database and Schema Blueprint successfully synthesized.")


if __name__ == "__main__":
    init_db()
